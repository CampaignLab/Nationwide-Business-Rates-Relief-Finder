"""Stage 4: assign each property a sector.

Precedence, highest first:
  1. mapping/text_flags.csv: regular expressions on description text or names
     (used for possible vape shops and adult gaming centres, which have no VOA code)
  2. mapping/scat_overrides.csv rows for a specific primary description code and SCAT code
  3. mapping/scat_overrides.csv rows with primary code '*' (any code) and a SCAT code
  4. mapping/sector_map.csv by primary description code

The description code in the list is the primary code plus an optional one-letter
secondary code (W, S, C or O), as described in Appendix 2 of the VOA specification.
"""
import csv

from common import MAPPING, WORK, connect, count, get_logger, sql_path, write_stage_log

log = get_logger("04_sector")

SECTORS = {"retail", "hospitality", "leisure", "pub", "possible_vape_shop", "possible_adult_gaming_centre", "other"}
RHL_SECTORS = ("retail", "hospitality", "leisure", "pub")
CONFIDENCE = {"high", "medium", "low"}
SECONDARY_CODES = "WSCO"
TEXT_FIELDS = {"description_text", "firm_name", "number_or_name"}


def read_csv(name):
    with open(MAPPING / name, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for line, r in enumerate(rows, start=2):
        if None in r or None in r.values():
            raise SystemExit(f"{name} line {line}: wrong number of fields (quote any value containing a comma)")
        if r["sector"] not in SECTORS:
            raise SystemExit(f"{name}: unknown sector {r['sector']!r}")
        if r["confidence"] not in CONFIDENCE:
            raise SystemExit(f"{name}: unknown confidence {r['confidence']!r}")
    return rows


def lit(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def main():
    sector_map = read_csv("sector_map.csv")
    overrides = read_csv("scat_overrides.csv")
    text_flags = read_csv("text_flags.csv")
    awaiting = {name: sum(r["review_status"] != "signed_off" for r in rows)
                for name, rows in [("sector_map.csv", sector_map), ("scat_overrides.csv", overrides),
                                   ("text_flags.csv", text_flags)]}
    if any(awaiting.values()):
        log.warning("Mapping rows awaiting human review: %s. Stage 7 output is not yet trusted.", awaiting)

    con = connect()
    con.execute("CREATE TABLE sector_map (code VARCHAR, sector VARCHAR, confidence VARCHAR)")
    con.executemany("INSERT INTO sector_map VALUES (?, ?, ?)",
                    [(r["primary_description_code"], r["sector"], r["confidence"]) for r in sector_map])
    con.execute("CREATE TABLE overrides (code VARCHAR, scat VARCHAR, sector VARCHAR, confidence VARCHAR)")
    con.executemany("INSERT INTO overrides VALUES (?, ?, ?, ?)",
                    [(r["primary_description_code"], r["scat_code"], r["sector"], r["confidence"]) for r in overrides])

    text_cases_sector, text_cases_conf = [], []
    for r in text_flags:
        fields = r["fields"].split(";")
        if not set(fields) <= TEXT_FIELDS:
            raise SystemExit(f"text_flags.csv: unknown fields {fields}")
        cond = " OR ".join(f"regexp_matches(coalesce(e.{f}, ''), {lit(r['pattern'])})" for f in fields)
        text_cases_sector.append(f"WHEN {cond} THEN {lit(r['sector'])}")
        text_cases_conf.append(f"WHEN {cond} THEN {lit(r['confidence'])}")

    con.execute(f"CREATE VIEW england AS SELECT * FROM read_parquet('{sql_path(WORK / 'england.parquet')}')")
    rows_in = count(con, "england")

    con.execute(f"""
        CREATE TABLE coded AS
        SELECT e.*,
               CASE WHEN e.description_code IN (SELECT code FROM sector_map) THEN e.description_code
                    WHEN left(e.description_code, length(e.description_code) - 1) IN (SELECT code FROM sector_map)
                         AND right(e.description_code, 1) IN ({', '.join(lit(c) for c in SECONDARY_CODES)})
                    THEN left(e.description_code, length(e.description_code) - 1) END AS primary_description_code,
               left(e.scat_code, 3) AS scat3,
               CASE {' '.join(text_cases_sector)} END AS text_sector,
               CASE {' '.join(text_cases_conf)} END AS text_confidence
        FROM england e
    """)
    con.execute("""
        CREATE TABLE sectored AS
        SELECT c.* EXCLUDE (text_sector, text_confidence, scat3),
               coalesce(c.text_sector, o1.sector, o2.sector, m.sector, 'other') AS sector,
               coalesce(c.text_confidence, o1.confidence, o2.confidence, m.confidence, 'low') AS sector_confidence,
               CASE WHEN c.text_sector IS NOT NULL THEN 'text_flag'
                    WHEN o1.sector IS NOT NULL THEN 'scat_override'
                    WHEN o2.sector IS NOT NULL THEN 'scat_override_any_code'
                    WHEN m.sector IS NOT NULL THEN 'primary_code'
                    ELSE 'unmapped' END AS sector_source
        FROM coded c
        LEFT JOIN overrides o1 ON o1.code = c.primary_description_code AND o1.scat = c.scat3
        LEFT JOIN overrides o2 ON o2.code = '*' AND o2.scat = c.scat3
        LEFT JOIN sector_map m ON m.code = c.primary_description_code
    """)
    con.execute(f"ALTER TABLE sectored ADD COLUMN is_rhl BOOLEAN")
    con.execute(f"UPDATE sectored SET is_rhl = sector IN ({', '.join(lit(s) for s in RHL_SECTORS)})")
    rows_out = count(con, "sectored")
    assert rows_out == rows_in

    unmapped = con.execute("SELECT description_code, count(*) FROM sectored WHERE sector_source = 'unmapped' GROUP BY 1").fetchall()
    if unmapped:
        log.warning("Description codes not in sector_map.csv (set to 'other', low confidence): %s", unmapped)

    con.execute(f"COPY sectored TO '{sql_path(WORK / 'sectored.parquet')}' (FORMAT parquet)")
    con.execute(f"""
        COPY (SELECT sector, sector_confidence, sector_source, primary_description_code, left(scat_code, 3) AS scat3,
                     count(*) AS properties, count(*) FILTER (WHERE rateable_value < 21000) AS properties_under_21000,
                     mode(description_text) AS most_common_description
              FROM sectored GROUP BY ALL ORDER BY sector, properties DESC)
        TO '{sql_path(WORK / 'sector_coverage.csv')}' (HEADER)
    """)
    by_sector = dict(con.execute("SELECT sector, count(*) FROM sectored GROUP BY 1 ORDER BY 2 DESC").fetchall())
    by_source = dict(con.execute("SELECT sector_source, count(*) FROM sectored GROUP BY 1 ORDER BY 2 DESC").fetchall())
    by_conf = dict(con.execute("SELECT sector_confidence, count(*) FROM sectored GROUP BY 1 ORDER BY 2 DESC").fetchall())
    log.info("Rows in: %d. Rows out: %d", rows_in, rows_out)
    log.info("By sector: %s", by_sector)
    log.info("By source: %s", by_source)
    log.info("By confidence: %s", by_conf)
    write_stage_log("04_sector", rows_in=rows_in, rows_out=rows_out, by_sector=by_sector, by_source=by_source,
                    by_confidence=by_conf, unmapped_codes=unmapped, mapping_rows_awaiting_review=awaiting)


if __name__ == "__main__":
    main()
