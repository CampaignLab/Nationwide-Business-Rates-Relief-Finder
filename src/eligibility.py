"""Small Business Rate Relief screening logic.

Every threshold comes from config/rules.yaml. The result is a screening flag:
the VOA list does not show who pays rates, who receives relief, or whether a
property is occupied.
"""
from dataclasses import dataclass

LIKELY_NOW = "likely_eligible_now"
POSSIBLY_NOW = "possibly_eligible_now"
NOT_FLAGGED = "not_flagged"
ELIGIBLE_APR_2027 = "eligible_from_apr_2027"
EXCLUDED_VAPE = "excluded_possible_vape_shop"

RHL_SECTORS = frozenset({"retail", "hospitality", "leisure", "pub"})
VAPE = "possible_vape_shop"
AGC = "possible_adult_gaming_centre"


@dataclass(frozen=True)
class Property:
    rv: int
    sector: str = "other"
    is_london: bool = False
    firm_named: bool = False
    firm_property_count: int | None = None
    firm_total_rv: int | None = None
    firm_other_max_rv: int | None = None


@dataclass(frozen=True)
class Result:
    status_now: str
    status_from_apr_2027: str
    reason: str
    relief_now: float
    relief_from_apr_2027: float
    target_new_full_relief: bool


def money(v: int) -> str:
    return f"£{v:,}"


def taper_relief(rv: int, full_relief_max_rv: int, taper_end_rv: int) -> float:
    """Share of the bill relieved: 1 up to full_relief_max_rv, falling linearly to 0 at taper_end_rv."""
    if rv <= full_relief_max_rv:
        return 1.0
    if rv >= taper_end_rv:
        return 0.0
    return 1 - (rv - full_relief_max_rv) / (taper_end_rv - full_relief_max_rv)


def _multi_property(p: Property, other_max_allowed: int, aggregate_limit: int, limit_label: str):
    """Return (state, text). State is 'unnamed', 'single', 'passes' or 'fails'."""
    if not p.firm_named:
        return "unnamed", "No firm name is held in the list, so other properties could not be checked."
    if not p.firm_property_count or p.firm_property_count <= 1:
        return "single", "No other properties found under this firm name."
    n = p.firm_property_count
    total = p.firm_total_rv or 0
    other_max = p.firm_other_max_rv or 0
    problems = []
    if other_max > other_max_allowed:
        problems.append(f"at least one other property is above {money(other_max_allowed)}")
    if total > aggregate_limit:
        problems.append(f"the combined rateable value of {money(total)} is above the {limit_label} limit of {money(aggregate_limit)}")
    caveat = "Matching is by firm name only and does not prove common ownership."
    if problems:
        return "fails", (f"The firm name appears on {n:,} properties in England, and {' and '.join(problems)}. "
                         f"If they are the same business, relief is unlikely. {caveat}")
    return "passes", (f"The firm name appears on {n:,} properties in England. Each other property is "
                      f"{money(other_max_allowed)} or less and the combined value of {money(total)} is within the "
                      f"{limit_label} limit of {money(aggregate_limit)}, so the multiple-property conditions may be met. {caveat}")


def _general(p: Property, full: int, taper_end: int, other_max_allowed: int, aggregate_limit: int, limit_label: str):
    """Apply the general SBRR test. Returns (status, text, relief)."""
    if p.rv == 0:
        return NOT_FLAGGED, "Rateable value is £0, so there is no rates bill to relieve.", 0.0
    if p.rv >= taper_end:
        return NOT_FLAGGED, f"Rateable value {money(p.rv)} is {money(taper_end)} or more.", 0.0
    state, multi_text = _multi_property(p, other_max_allowed, aggregate_limit, limit_label)
    relief = taper_relief(p.rv, full, taper_end)
    if p.rv <= full:
        rv_text = f"Rateable value {money(p.rv)} is {money(full)} or less."
    else:
        rv_text = (f"Rateable value {money(p.rv)} is between {money(full)} and {money(taper_end)}, "
                   f"so tapered relief of about {relief:.0%} may apply.")
    if state == "fails":
        return NOT_FLAGGED, f"{rv_text} {multi_text}", 0.0
    if p.rv <= full and state in ("unnamed", "single"):
        return LIKELY_NOW, f"{rv_text} {multi_text}", relief
    return POSSIBLY_NOW, f"{rv_text} {multi_text}", relief


def assess(p: Property, rules: dict) -> Result:
    g = rules["sbrr_general"]
    full, taper_end, other_max = g["full_relief_max_rv"], g["taper_end_rv"], g["other_property_max_rv"]
    before = g["aggregate_max_rv_before"]
    if p.is_london:
        agg_now, label_now = before["london"], "London"
    else:
        agg_now, label_now = before["england_outside_london"], "England outside London"
    agg_2027, label_2027 = g["aggregate_max_rv_after"]["england_wide"], "England-wide"
    rhl = rules["sbrr_rhl_from_april_2027"]

    status_now, text_now, relief_now = _general(p, full, taper_end, other_max, agg_now, label_now)

    # A possible vape shop is a shop, so it is assessed as retail before the exclusion is applied.
    sector = "retail" if p.sector == VAPE else p.sector
    if sector in RHL_SECTORS and p.rv > full:
        rhl_full, rhl_end = rhl["full_relief_max_rv"], rhl["taper_end_rv"]
        status_27, text_27, relief_27 = _general(p, rhl_full, rhl_end, other_max, agg_2027, label_2027)
        if status_27 != NOT_FLAGGED:
            status_27 = ELIGIBLE_APR_2027
        if p.rv < rhl_end:
            text_27 = (f"Sector is {sector}. Qualifying retail, hospitality and leisure properties are announced "
                       f"to get full relief up to {money(rhl_full)}, tapering to nothing at {money(rhl_end)}. {text_27}")
    else:
        status_27, text_27, relief_27 = _general(p, full, taper_end, other_max, agg_2027, label_2027)
        if p.sector == AGC and status_27 != NOT_FLAGGED:
            text_27 = (f"Possible adult gaming centre, which is announced to stay on the general "
                       f"{money(full)} and {money(taper_end)} thresholds. {text_27}")

    if p.sector == VAPE and status_27 != NOT_FLAGGED:
        status_27, relief_27 = EXCLUDED_VAPE, 0.0
        text_27 = ("Possible vape shop. Vape shops are announced to lose Small Business Rate Relief from "
                   f"1 April 2027. The definition is not yet published. If it is not a vape shop: {text_27}")

    reason = f"Now: {text_now} From 1 April 2027: {'No change.' if text_27 == text_now else text_27}"
    target = (p.sector in RHL_SECTORS and full < p.rv <= rhl["full_relief_max_rv"]
              and status_27 == ELIGIBLE_APR_2027 and relief_27 == 1.0)
    return Result(status_now, status_27, reason, relief_now, relief_27, target)
