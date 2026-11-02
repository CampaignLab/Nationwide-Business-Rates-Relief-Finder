"""Checks on real data, written into out/run_report.md by stage 7."""
import duckdb

EARLEY_DISTRICT = "RG6"
EARLEY_CONSTITUENCY = "Earley and Woodley"
SAMPLE_SEED = 0.42


def md_table(headers, rows) -> str:
    def cell(v):
        if v is None:
            return ""
        if isinstance(v, bool):
            return "yes" if v else "no"
        if isinstance(v, float):
            return f"{v:.1%}" if v <= 1 else f"{v:,.0f}"
        if isinstance(v, int):
            return f"{v:,}"
        return str(v).replace("|", "/")
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def earley(con: duckdb.DuckDBPyConnection) -> tuple[str, dict]:
    by_constituency = con.execute(f"""
        SELECT coalesce(constituency_name, '(no constituency)'), ba_name, count(*)
        FROM flagged WHERE split_part(postcode, ' ', 1) = '{EARLEY_DISTRICT}'
        GROUP BY ALL ORDER BY 3 DESC
    """).fetchall()

    definitions = [
        ("Rateable value £1 to £12,000 (any sector)", "rateable_value BETWEEN 1 AND 12000"),
        ("As above, excluding firm names found on more than one property",
         "rateable_value BETWEEN 1 AND 12000 AND NOT multi_property_flag"),
        ("Rateable value £12,001 to £14,999 (any sector)", "rateable_value BETWEEN 12001 AND 14999"),
        ("April 2027 view: retail, hospitality or leisure at £12,001 to £21,000",
         "is_rhl AND rateable_value BETWEEN 12001 AND 21000"),
        ("Supplementary: retail, hospitality or leisure at £1 to £12,000", "is_rhl AND rateable_value BETWEEN 1 AND 12000"),
        ("Supplementary: flagged under either status", "status_now <> 'not_flagged' OR status_from_apr_2027 <> 'not_flagged'"),
    ]
    scopes = [
        (f"{EARLEY_DISTRICT} in {EARLEY_CONSTITUENCY}",
         f"split_part(postcode, ' ', 1) = '{EARLEY_DISTRICT}' AND constituency_name = '{EARLEY_CONSTITUENCY}'"),
        (f"All {EARLEY_DISTRICT}", f"split_part(postcode, ' ', 1) = '{EARLEY_DISTRICT}'"),
    ]
    rows, counts = [], {}
    for label, cond in definitions:
        row = [label]
        for scope_label, scope in scopes:
            n = con.execute(f"SELECT count(*) FROM flagged WHERE ({scope}) AND ({cond})").fetchone()[0]
            row.append(n)
            counts[(label, scope_label)] = n
        rows.append(row)
    zero = con.execute(f"SELECT count(*) FROM flagged WHERE {scopes[0][1]} AND rateable_value = 0").fetchone()[0]

    main_counts = [r[1] for r in rows[:4]]
    closest = min(range(4), key=lambda i: abs(main_counts[i] - 100))

    sample = con.execute(f"""
        SELECT uarn, full_property_identifier, postcode, rateable_value, description_text, sector,
               status_now, status_from_apr_2027
        FROM flagged
        WHERE {scopes[0][1]} AND (status_now <> 'not_flagged' OR status_from_apr_2027 <> 'not_flagged')
        ORDER BY hash(uarn || '{SAMPLE_SEED}') LIMIT 20
    """).fetchall()

    text = f"""## Earley benchmark

The brief refers to "Earley (Reading East)". Reading East is not a 2024 constituency. Under the 2024
boundaries in ONSPD, the {EARLEY_DISTRICT} postcode district is split as follows:

{md_table(["Constituency", "Billing authority", "Properties"], by_constituency)}

Counts use the {EARLEY_DISTRICT} district within {EARLEY_CONSTITUENCY} (the constituency that now holds most
of Earley), with all of {EARLEY_DISTRICT} shown for comparison. Properties with a rateable value of £0
({zero:,} in the first scope) are left out of the rateable value bands.

{md_table(["Definition", scopes[0][0], scopes[1][0]], rows)}

The reported figure of "just under 100" is a loose reference from an analysis whose method is not
available. Of the four definitions in the brief, the closest is: **{definitions[closest][0]}**
({main_counts[closest]:,}). The rules have not been tuned to match it.

### Sample of 20 flagged Earley properties for human review

{md_table(["UARN", "Address", "Postcode", "Rateable value", "VOA description", "Sector", "Status now", "Status from April 2027"],
          [(u, a, p, f"£{rv:,}", d, s, sn, s27) for u, a, p, rv, d, s, sn, s27 in sample])}
"""
    return text, {"by_definition": {f"{k[0]} | {k[1]}": v for k, v in counts.items()},
                  "closest_definition": definitions[closest][0]}


def plausibility(con: duckdb.DuckDBPyConnection) -> tuple[str, dict]:
    total, at_or_below, band = con.execute("""
        SELECT count(*), count(*) FILTER (WHERE rateable_value <= 18000),
               count(*) FILTER (WHERE rateable_value BETWEEN 12001 AND 18000)
        FROM flagged WHERE is_rhl
    """).fetchone()
    by_sector = con.execute("""
        SELECT sector, count(*), count(*) FILTER (WHERE rateable_value <= 18000),
               count(*) FILTER (WHERE rateable_value <= 18000) / count(*)
        FROM flagged WHERE is_rhl GROUP BY 1 ORDER BY 2 DESC
    """).fetchall()
    by_code = con.execute("""
        SELECT primary_description_code, any_value(sector), count(*) FILTER (WHERE rateable_value BETWEEN 12001 AND 18000)
        FROM flagged WHERE is_rhl GROUP BY 1 ORDER BY 3 DESC LIMIT 10
    """).fetchall()
    share = at_or_below / total
    if 0.4 <= share <= 0.85 and 35_000 <= band <= 200_000:
        verdict = (f"A share of {share:.0%} against \"half\" and {band:,} against \"about 70,000\" is higher, as expected "
                   "for a property count, and does not on its own suggest the sector mapping is badly wrong.")
    else:
        verdict = (f"**A share of {share:.0%} against \"half\" and {band:,} against \"about 70,000\" is a large gap. "
                   "Review the sector mapping before relying on the April 2027 statuses.**")
    text = f"""## Plausibility check: retail, hospitality and leisure

The government says the 2027 change takes about 70,000 businesses out of rates and that half of all
retail, hospitality and leisure properties will pay none. This is a rough comparison, not a target.

- Properties mapped to retail, hospitality, leisure or pub in England: {total:,}
- Of these, rateable value £18,000 or less: {at_or_below:,} ({share:.1%})
- Of these, rateable value £12,001 to £18,000 (the band newly brought to full relief): {band:,}

{md_table(["Sector", "Properties", "£18,000 or less", "Share"], by_sector)}

Largest contributors to the £12,001 to £18,000 band, by primary description code:

{md_table(["Code", "Sector", "Properties £12,001 to £18,000"], by_code)}

Reading the comparison: the list counts properties, not businesses, and includes empty properties,
properties held by businesses with several sites, and self-catering holiday lets (code CH1), which must
meet letting conditions to be rated at all. Each of these pushes the property count above the number of
businesses that would actually pay nothing. {verdict}
"""
    return text, {"rhl_properties": total, "rhl_at_or_below_18000": at_or_below, "share": round(share, 4),
                  "rhl_12001_to_18000": band}


def spot_check(con: duckdb.DuckDBPyConnection) -> str:
    rows = con.execute(f"""
        SELECT uarn, ba_reference, ba_name, full_property_identifier, postcode, rateable_value, description_text,
               sector, status_now, status_from_apr_2027
        FROM flagged
        WHERE constituency_code IS NOT NULL
          AND (status_now <> 'not_flagged' OR status_from_apr_2027 <> 'not_flagged')
        ORDER BY hash(uarn || '{SAMPLE_SEED}') LIMIT 20
    """).fetchall()
    return f"""## Spot check: 20 random flagged properties

Check each against the VOA's online valuation search on GOV.UK ("Find a business rates valuation"),
searching by postcode and matching the address and rateable value. The UARN is the VOA's unique property
reference.

{md_table(["UARN", "BA reference", "Billing authority", "Address", "Postcode", "Rateable value", "VOA description", "Sector", "Status now", "Status from April 2027"],
          [(r[0], r[1], r[2], r[3], r[4], f"£{r[5]:,}", r[6], r[7], r[8], r[9]) for r in rows])}
"""
