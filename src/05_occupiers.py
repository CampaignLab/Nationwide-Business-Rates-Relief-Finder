"""Stage 5: group properties by normalised firm name.

The firm name field is filled in for a small minority of entries and is not a
reliable record of the occupier. Grouping by name is a fuzzy match, so the
result is a flag for review, not a finding that one business holds the properties.

Normalisation: lowercase; '&' becomes 'and'; punctuation becomes a space;
'limited' becomes 'ltd'; whitespace is collapsed. Names that are placeholders
(see PLACEHOLDER_NAMES) or a single character are treated as blank and not grouped.
"""
from common import WORK, connect, count, get_logger, sql_path, write_stage_log

log = get_logger("05_occupiers")

PLACEHOLDER_NAMES = (
    "occupier", "the occupier", "occupiers", "the occupiers", "owner", "the owner", "owners",
    "the owners", "owner occupier", "proprietor", "the proprietor", "unknown", "vacant",
    "none", "na", "n a", "tba", "tbc",
    # Generic descriptions found in the firm name field rather than names.
    "shop", "store", "unit", "site", "hall", "mast", "office", "offices", "premises", "void",
)


def normalise_sql(col: str) -> str:
    s = f"lower(coalesce({col}, ''))"
    s = f"replace({s}, '&', ' and ')"
    s = f"regexp_replace({s}, '[^a-z0-9]+', ' ', 'g')"
    s = f"regexp_replace(' ' || {s} || ' ', ' limited ', ' ltd ', 'g')"
    s = f"trim(regexp_replace({s}, '\\s+', ' ', 'g'))"
    return s


def main():
    con = connect()
    con.execute(f"CREATE VIEW src AS SELECT * FROM read_parquet('{sql_path(WORK / 'sectored.parquet')}')")
    rows_in = count(con, "src")
    placeholders = ", ".join(f"'{p}'" for p in PLACEHOLDER_NAMES)
    con.execute(f"""
        CREATE TABLE named AS
        SELECT *, CASE WHEN n IN ({placeholders}) OR length(n) < 2 THEN NULL ELSE n END AS firm_name_normalised
        FROM (SELECT *, {normalise_sql('firm_name')} AS n FROM src)
    """)
    con.execute("""
        CREATE TABLE grouped AS
        SELECT * EXCLUDE (n),
            CASE WHEN firm_name_normalised IS NOT NULL THEN count(*) OVER nat END AS firm_property_count,
            CASE WHEN firm_name_normalised IS NOT NULL THEN sum(rateable_value) OVER nat END AS firm_total_rv,
            CASE WHEN firm_name_normalised IS NOT NULL THEN max(rateable_value) OVER (
                PARTITION BY firm_name_normalised ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                EXCLUDE CURRENT ROW) END AS firm_other_max_rv,
            CASE WHEN firm_name_normalised IS NOT NULL THEN count(*) OVER ba END AS firm_ba_property_count,
            CASE WHEN firm_name_normalised IS NOT NULL THEN sum(rateable_value) OVER ba END AS firm_ba_total_rv,
            coalesce(firm_name_normalised IS NOT NULL AND count(*) OVER nat > 1, false) AS multi_property_flag
        FROM named
        WINDOW nat AS (PARTITION BY firm_name_normalised),
               ba AS (PARTITION BY firm_name_normalised, ba_code)
    """)
    rows_out = count(con, "grouped")
    assert rows_out == rows_in
    con.execute(f"COPY grouped TO '{sql_path(WORK / 'occupiers.parquet')}' (FORMAT parquet)")

    q = lambda sql: con.execute(sql).fetchone()[0]
    stats = {
        "firm_name_present": q("SELECT count(*) FROM grouped WHERE firm_name IS NOT NULL AND trim(firm_name) <> ''"),
        "firm_name_placeholder_or_too_short": q("SELECT count(*) FROM grouped WHERE firm_name IS NOT NULL AND trim(firm_name) <> '' AND firm_name_normalised IS NULL"),
        "firm_name_grouped": q("SELECT count(*) FROM grouped WHERE firm_name_normalised IS NOT NULL"),
        "distinct_normalised_names": q("SELECT count(DISTINCT firm_name_normalised) FROM grouped"),
        "multi_property_flag_rows": q("SELECT count(*) FROM grouped WHERE multi_property_flag"),
    }
    top = con.execute("""SELECT firm_name_normalised, any_value(firm_property_count), any_value(firm_total_rv)
                         FROM grouped WHERE firm_name_normalised IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 15""").fetchall()
    log.info("Rows in: %d. Rows out: %d", rows_in, rows_out)
    for k, v in stats.items():
        log.info("%s: %d", k, v)
    log.info("Largest name groups: %s", top)
    write_stage_log("05_occupiers", rows_in=rows_in, rows_out=rows_out, **stats)


if __name__ == "__main__":
    main()
