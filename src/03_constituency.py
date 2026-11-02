"""Stage 3: assign each English property a 2024 parliamentary constituency.

Joins on postcode to the ONS Postcode Directory (ONSPD). England and Wales are
separated by the VOA billing authority code (mapping/billing_authorities.csv,
from Appendix 1 of the VOA specification), because the billing authority
decides which country's relief rules apply. ONSPD country is used as a cross-check.
"""
import re
import shutil
import zipfile

from common import MAPPING, RAW, WORK, connect, count, get_logger, sql_path, write_stage_log

log = get_logger("03_constituency")

# Field names verified against the ONSPD User Guide August 2026, Annex A.
# The year suffixes change between releases; check the guide when updating ONSPD.
ONSPD_FIELDS = {
    "pcds": "postcode (variable length, single space)",
    "doterm": "date of termination (null for live postcodes)",
    "ctry26cd": "country",
    "rgn26cd": "region (former GOR)",
    "pcon24cd": "Westminster parliamentary constituency (2024 boundaries)",
    "lad26cd": "local authority district",
}
ENGLAND = "E92000001"
LONDON_REGION = "E12000007"
MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], start=1)}


def find_onspd():
    found = []
    for p in RAW.glob("ONSPD_*.zip"):
        m = re.fullmatch(r"ONSPD_([A-Z]{3})_(\d{4})\.zip", p.name, flags=re.I)
        if m:
            found.append(((int(m.group(2)), MONTHS[m.group(1).upper()]), p))
    if not found:
        raise SystemExit("No ONSPD zip (ONSPD_MMM_YYYY.zip) found in data/raw/. Download the latest ONSPD release.")
    found.sort()
    if len(found) > 1:
        log.warning("Several ONSPD zips found; using the latest: %s", found[-1][1].name)
    return found[-1][1]


def extract(zf: zipfile.ZipFile, pattern: str, dest_dir, label: str):
    names = [n for n in zf.namelist() if re.search(pattern, n, flags=re.I)]
    if len(names) != 1:
        raise SystemExit(f"Expected one {label} file in the ONSPD zip matching {pattern!r}, found {names}")
    dest = dest_dir / re.sub(r"[^A-Za-z0-9_.]", "_", names[0].split("/")[-1])
    with zf.open(names[0]) as src, open(dest, "wb") as dst:
        shutil.copyfileobj(src, dst, length=1 << 24)
    return names[0], dest


def read_lookup(con, path, code_prefix: str, name_prefix: str, table: str):
    """Load an ONSPD names-and-codes file, whatever year suffix its columns carry."""
    for encoding in ("utf-8", "latin-1"):
        try:
            con.execute(f"CREATE OR REPLACE TABLE {table}_raw AS SELECT * FROM read_csv('{sql_path(path)}', header=true, all_varchar=true, encoding='{encoding}')")
            break
        except Exception:
            if encoding == "latin-1":
                raise
    cols = [r[0] for r in con.execute(f"DESCRIBE {table}_raw").fetchall()]
    code = next(c for c in cols if re.fullmatch(code_prefix + r"\d{2}CD", c, flags=re.I))
    name = next(c for c in cols if re.fullmatch(name_prefix + r"\d{2}NM", c, flags=re.I))
    con.execute(f'CREATE OR REPLACE TABLE {table} AS SELECT "{code}" AS code, "{name}" AS name FROM {table}_raw')
    return code, name


def main():
    onspd_zip = find_onspd()
    log.info("Using %s", onspd_zip.name)
    extract_dir = WORK / "_extract_onspd"
    shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir()
    with zipfile.ZipFile(onspd_zip) as zf:
        data_member, data_csv = extract(zf, r"^Data/ONSPD_[A-Z]{3}_\d{4}_UK\.csv$", extract_dir, "ONSPD data")
        pcon_member, pcon_csv = extract(zf, r"^Documents/PCON .*\.csv$", extract_dir, "constituency names")
        rgn_member, rgn_csv = extract(zf, r"^Documents/RGN .*\.csv$", extract_dir, "region names")

    con = connect()
    header = con.execute(f"SELECT * FROM read_csv('{sql_path(data_csv)}', header=true, all_varchar=true) LIMIT 0").description
    available = {d[0].lower(): d[0] for d in header}
    missing = [f for f in ONSPD_FIELDS if f not in available]
    if missing:
        raise SystemExit(
            f"ONSPD fields {missing} not found in {data_member}. Check Annex A of this release's user guide "
            "and update ONSPD_FIELDS in src/03_constituency.py.")
    select = ", ".join(f'"{available[f]}" AS {f}' for f in ONSPD_FIELDS)
    con.execute(f"CREATE TABLE onspd AS SELECT {select} FROM read_csv('{sql_path(data_csv)}', header=true, all_varchar=true)")
    dupes = con.execute("SELECT count(*) - count(DISTINCT pcds) FROM onspd").fetchone()[0]
    if dupes:
        raise SystemExit(f"ONSPD has {dupes} duplicate postcodes; the join would multiply rows.")
    log.info("ONSPD postcodes loaded: %d", count(con, "onspd"))

    read_lookup(con, pcon_csv, "PCON", "PCON", "pcon_names")
    read_lookup(con, rgn_csv, "RGN", "RGN", "rgn_names")
    con.execute(f"""CREATE TABLE ba AS SELECT * FROM read_csv('{sql_path(MAPPING / 'billing_authorities.csv')}',
                    header=true, types={{'ba_code': 'VARCHAR', 'is_london': 'BOOLEAN'}})""")

    con.execute(f"CREATE VIEW clean AS SELECT * FROM read_parquet('{sql_path(WORK / 'clean.parquet')}')")
    rows_in = count(con, "clean")
    unknown_ba = con.execute("SELECT count(*) FROM clean LEFT JOIN ba USING (ba_code) WHERE ba.ba_code IS NULL").fetchone()[0]
    if unknown_ba:
        raise SystemExit(f"{unknown_ba} rows have a billing authority code missing from mapping/billing_authorities.csv")

    con.execute("""
        CREATE TABLE joined AS
        SELECT c.*, ba.ba_name, ba.country AS ba_country, ba.is_london,
               o.pcds IS NOT NULL AS postcode_matched,
               o.doterm IS NOT NULL AS postcode_terminated,
               o.ctry26cd AS country_code, o.rgn26cd AS region_code, o.lad26cd AS onspd_lad_code,
               o.pcon24cd AS constituency_code, p.name AS constituency_name, r.name AS region_name
        FROM clean c
        JOIN ba USING (ba_code)
        LEFT JOIN onspd o ON o.pcds = c.postcode
        LEFT JOIN pcon_names p ON p.code = o.pcon24cd
        LEFT JOIN rgn_names r ON r.code = o.rgn26cd
    """)
    assert count(con, "joined") == rows_in

    q = lambda sql: con.execute(sql).fetchone()[0]
    welsh_ba = q("SELECT count(*) FROM joined WHERE ba_country = 'Wales'")
    english_ba = q("SELECT count(*) FROM joined WHERE ba_country = 'England'")
    matched = q("SELECT count(*) FROM joined WHERE ba_country = 'England' AND postcode_matched")
    matched_terminated = q("SELECT count(*) FROM joined WHERE ba_country = 'England' AND postcode_terminated")
    unmatched = english_ba - matched
    outside_england = q("SELECT count(*) FROM joined WHERE ba_country = 'England' AND postcode_matched AND country_code <> 'E92000001'")
    outside_by_country = dict(con.execute("""SELECT country_code, count(*) FROM joined
        WHERE ba_country = 'England' AND postcode_matched AND country_code <> 'E92000001' GROUP BY 1""").fetchall())
    no_pcon_name = q("SELECT count(*) FROM joined WHERE ba_country = 'England' AND postcode_matched AND constituency_name IS NULL")
    welsh_ba_in_england = q("SELECT count(*) FROM joined WHERE ba_country = 'Wales' AND country_code = 'E92000001'")
    london_ba_not_region = q(f"SELECT count(*) FROM joined WHERE ba_country = 'England' AND is_london AND postcode_matched AND region_code <> '{LONDON_REGION}'")
    london_region_not_ba = q(f"SELECT count(*) FROM joined WHERE ba_country = 'England' AND NOT is_london AND region_code = '{LONDON_REGION}'")

    # Unmatched postcodes, with a check on whether the postcode district exists in ONSPD.
    con.execute("CREATE TABLE districts AS SELECT DISTINCT split_part(pcds, ' ', 1) AS district FROM onspd")
    con.execute(f"""
        COPY (
            SELECT j.postcode, count(*) AS properties, any_value(j.ba_code) AS ba_code, any_value(j.ba_name) AS ba_name,
                   d.district IS NOT NULL AS district_in_onspd,
                   any_value(j.full_property_identifier) AS example_address
            FROM joined j LEFT JOIN districts d ON d.district = split_part(j.postcode, ' ', 1)
            WHERE j.ba_country = 'England' AND NOT j.postcode_matched
            GROUP BY j.postcode, d.district IS NOT NULL
            ORDER BY properties DESC, j.postcode
        ) TO '{sql_path(WORK / 'unmatched_postcodes.csv')}' (HEADER)
    """)
    unmatched_district_known = q("""SELECT count(*) FROM joined j JOIN districts d ON d.district = split_part(j.postcode, ' ', 1)
                                     WHERE j.ba_country = 'England' AND NOT j.postcode_matched""")

    # Output: English billing authorities only. Rows whose postcode ONSPD places outside
    # England are kept but given no constituency, so they appear in no constituency file.
    con.execute(f"""
        COPY (
            SELECT * EXCLUDE (ba_country, constituency_code, constituency_name),
                   CASE WHEN country_code = '{ENGLAND}' THEN constituency_code END AS constituency_code,
                   CASE WHEN country_code = '{ENGLAND}' THEN constituency_name END AS constituency_name
            FROM joined WHERE ba_country = 'England'
        ) TO '{sql_path(WORK / 'england.parquet')}' (FORMAT parquet)
    """)
    rows_out = english_ba
    with_constituency = matched - outside_england
    match_rate = matched / english_ba

    report = {
        "onspd_release": onspd_zip.name,
        "onspd_data_file": data_member,
        "constituency_names_file": pcon_member,
        "region_names_file": rgn_member,
        "welsh_billing_authority_rows_excluded": welsh_ba,
        "english_billing_authority_rows": english_ba,
        "matched": matched,
        "matched_to_terminated_postcode": matched_terminated,
        "unmatched": unmatched,
        "unmatched_with_known_postcode_district": unmatched_district_known,
        "matched_but_onspd_country_not_england": outside_england,
        "matched_but_onspd_country_not_england_by_country": outside_by_country,
        "matched_but_no_constituency_name": no_pcon_name,
        "rows_with_english_constituency": with_constituency,
        "match_rate": round(match_rate, 5),
        "constituency_rate": round(with_constituency / english_ba, 5),
        "welsh_billing_authority_rows_with_english_postcode": welsh_ba_in_england,
        "london_ba_but_onspd_region_not_london": london_ba_not_region,
        "onspd_region_london_but_ba_not_london": london_region_not_ba,
    }
    shutil.rmtree(extract_dir, ignore_errors=True)
    for k, v in report.items():
        log.info("%s: %s", k, v)
    log.info("Rows in: %d. Rows out (English billing authorities): %d", rows_in, rows_out)
    write_stage_log("03_constituency", rows_in=rows_in, rows_out=rows_out, **report)


if __name__ == "__main__":
    main()
