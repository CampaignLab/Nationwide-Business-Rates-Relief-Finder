import copy
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from eligibility import (  # noqa: E402
    ELIGIBLE_APR_2027, EXCLUDED_VAPE, LIKELY_NOW, NOT_FLAGGED, POSSIBLY_NOW, Property, assess, taper_relief,
)

CONFIG = Path(__file__).resolve().parent.parent / "config" / "rules.yaml"


@pytest.fixture(scope="module")
def rules():
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_config_values_match_announced_rules(rules):
    g = rules["sbrr_general"]
    assert (g["full_relief_max_rv"], g["taper_end_rv"], g["other_property_max_rv"]) == (12000, 15000, 2899)
    assert g["aggregate_max_rv_before"]["england_outside_london"] == 19999
    assert g["aggregate_max_rv_before"]["london"] == 27999
    assert g["aggregate_max_rv_after"]["england_wide"] == 29999
    r = rules["sbrr_rhl_from_april_2027"]
    assert (r["full_relief_max_rv"], r["taper_end_rv"]) == (18000, 21000)


# Taper formula

@pytest.mark.parametrize("rv, full, end, expected", [
    (13500, 12000, 15000, 0.5),
    (19500, 18000, 21000, 0.5),
    (12000, 12000, 15000, 1.0),
    (15000, 12000, 15000, 0.0),
    (18000, 18000, 21000, 1.0),
    (21000, 18000, 21000, 0.0),
    (0, 12000, 15000, 1.0),
])
def test_taper(rv, full, end, expected):
    assert taper_relief(rv, full, end) == pytest.approx(expected)


def test_taper_from_assess(rules):
    assert assess(Property(13500), rules).relief_now == pytest.approx(0.5)
    assert assess(Property(19500, sector="retail"), rules).relief_from_apr_2027 == pytest.approx(0.5)


# General thresholds, single property or no firm name

@pytest.mark.parametrize("rv, now", [
    (1, LIKELY_NOW),
    (12000, LIKELY_NOW),
    (12001, POSSIBLY_NOW),
    (14999, POSSIBLY_NOW),
    (15000, NOT_FLAGGED),
    (17999, NOT_FLAGGED),
    (18000, NOT_FLAGGED),
    (21000, NOT_FLAGGED),
])
def test_general_thresholds_other_sector(rules, rv, now):
    r = assess(Property(rv, sector="other"), rules)
    assert r.status_now == now
    assert r.status_from_apr_2027 == now


def test_zero_rateable_value_not_flagged(rules):
    r = assess(Property(0, sector="retail"), rules)
    assert (r.status_now, r.status_from_apr_2027) == (NOT_FLAGGED, NOT_FLAGGED)


# Retail, hospitality and leisure from April 2027

@pytest.mark.parametrize("rv, now, apr27, relief27", [
    (12000, LIKELY_NOW, LIKELY_NOW, 1.0),
    (12001, POSSIBLY_NOW, ELIGIBLE_APR_2027, 1.0),
    (14999, POSSIBLY_NOW, ELIGIBLE_APR_2027, 1.0),
    (15000, NOT_FLAGGED, ELIGIBLE_APR_2027, 1.0),
    (17999, NOT_FLAGGED, ELIGIBLE_APR_2027, 1.0),
    (18000, NOT_FLAGGED, ELIGIBLE_APR_2027, 1.0),
    (20999, NOT_FLAGGED, ELIGIBLE_APR_2027, 1 / 3000),
    (21000, NOT_FLAGGED, NOT_FLAGGED, 0.0),
])
@pytest.mark.parametrize("sector", ["retail", "hospitality", "leisure", "pub"])
def test_rhl_thresholds(rules, sector, rv, now, apr27, relief27):
    r = assess(Property(rv, sector=sector), rules)
    assert r.status_now == now
    assert r.status_from_apr_2027 == apr27
    assert r.relief_from_apr_2027 == pytest.approx(relief27)


# Multiple properties

def named(rv, count=1, total=None, other_max=None, **kw):
    return Property(rv, firm_named=True, firm_property_count=count,
                    firm_total_rv=total if total is not None else rv, firm_other_max_rv=other_max, **kw)


def test_single_named_property_is_likely(rules):
    r = assess(named(11500), rules)
    assert r.status_now == LIKELY_NOW
    assert "No other properties found under this firm name." in r.reason


def test_unnamed_property_says_not_checked(rules):
    assert "could not be checked" in assess(Property(11500), rules).reason


def test_multi_property_passing_is_possibly(rules):
    r = assess(named(11000, count=3, total=16000, other_max=2899), rules)
    assert r.status_now == POSSIBLY_NOW
    assert "may be met" in r.reason


def test_other_property_at_2900_fails(rules):
    r = assess(named(11000, count=2, total=13900, other_max=2900), rules)
    assert r.status_now == NOT_FLAGGED
    assert r.status_from_apr_2027 == NOT_FLAGGED


def test_aggregate_limit_outside_london(rules):
    at_limit = assess(named(11000, count=4, total=19999, other_max=2899), rules)
    over = assess(named(11000, count=4, total=20000, other_max=2899), rules)
    assert at_limit.status_now == POSSIBLY_NOW
    assert over.status_now == NOT_FLAGGED
    # The 2027 England-wide limit is higher, so the same firm may pass.
    assert over.status_from_apr_2027 == POSSIBLY_NOW


def test_aggregate_limit_from_april_2027(rules):
    at_limit = assess(named(11000, count=8, total=29999, other_max=2899), rules)
    over = assess(named(11000, count=8, total=30000, other_max=2899), rules)
    assert at_limit.status_from_apr_2027 == POSSIBLY_NOW
    assert over.status_from_apr_2027 == NOT_FLAGGED


def test_london_has_higher_aggregate_limit_now(rules):
    london = assess(named(11000, count=6, total=25000, other_max=2899, is_london=True), rules)
    elsewhere = assess(named(11000, count=6, total=25000, other_max=2899, is_london=False), rules)
    assert london.status_now == POSSIBLY_NOW
    assert elsewhere.status_now == NOT_FLAGGED
    assert assess(named(11000, count=6, total=27999, other_max=2899, is_london=True), rules).status_now == POSSIBLY_NOW
    assert assess(named(11000, count=6, total=28000, other_max=2899, is_london=True), rules).status_now == NOT_FLAGGED


def test_multi_property_rhl_in_2027_band(rules):
    passes = assess(named(16000, count=2, total=18000, other_max=2000, sector="retail"), rules)
    fails = assess(named(16000, count=2, total=19000, other_max=3000, sector="retail"), rules)
    assert passes.status_from_apr_2027 == ELIGIBLE_APR_2027
    assert fails.status_from_apr_2027 == NOT_FLAGGED


# Exclusions

def test_vape_shop_excluded_from_april_2027(rules):
    r = assess(Property(10000, sector="possible_vape_shop"), rules)
    assert r.status_now == LIKELY_NOW
    assert r.status_from_apr_2027 == EXCLUDED_VAPE
    assert r.relief_from_apr_2027 == 0.0


def test_vape_shop_in_rhl_band_excluded(rules):
    r = assess(Property(16000, sector="possible_vape_shop"), rules)
    assert r.status_now == NOT_FLAGGED
    assert r.status_from_apr_2027 == EXCLUDED_VAPE


def test_large_vape_shop_not_flagged(rules):
    r = assess(Property(30000, sector="possible_vape_shop"), rules)
    assert (r.status_now, r.status_from_apr_2027) == (NOT_FLAGGED, NOT_FLAGGED)


@pytest.mark.parametrize("rv, apr27", [
    (12000, LIKELY_NOW),
    (12001, POSSIBLY_NOW),
    (14999, POSSIBLY_NOW),
    (15000, NOT_FLAGGED),
    (17999, NOT_FLAGGED),
])
def test_adult_gaming_centre_keeps_general_thresholds(rules, rv, apr27):
    r = assess(Property(rv, sector="possible_adult_gaming_centre"), rules)
    assert r.status_from_apr_2027 == apr27


# Thresholds come from config, not code

def test_thresholds_follow_config(rules):
    changed = copy.deepcopy(rules)
    changed["sbrr_general"]["full_relief_max_rv"] = 10000
    changed["sbrr_rhl_from_april_2027"]["taper_end_rv"] = 25000
    assert assess(Property(11000), changed).status_now == POSSIBLY_NOW
    assert assess(Property(23000, sector="retail"), changed).status_from_apr_2027 == ELIGIBLE_APR_2027


# Wording

@pytest.mark.parametrize("p", [
    Property(11500), Property(13000), Property(16000, sector="retail"), Property(16000, sector="possible_vape_shop"),
    named(11000, count=3, total=16000, other_max=2899), named(11000, count=2, total=13900, other_max=2900),
])
def test_reason_never_claims_relief(rules, p):
    reason = assess(p, rules).reason.lower()
    for phrase in ("confirmed", "is eligible", "receives relief", "will get"):
        assert phrase not in reason


def test_reason_example(rules):
    r = assess(named(11500), rules)
    assert r.reason.startswith("Now: Rateable value £11,500 is £12,000 or less. No other properties found under this firm name.")
