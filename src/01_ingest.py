"""Stage 1: load the VOA 2026 list entries baseline file into Parquet.

Column names and order follow the VOA Rating List Data Specification,
Part two, "List entry data items" (items 1 to 28). Each record ends with a
trailing asterisk, which produces an empty 29th field; this is checked and dropped.
"""
import re
import shutil
import zipfile
from datetime import datetime

from common import RAW, WORK, connect, count, get_logger, sql_path, write_stage_log

log = get_logger("01_ingest")

# Items 1 to 28 of the list entry specification, in file order.
VOA_COLUMNS = [
    "entry_number",              # 1 Incrementing Entry Number
    "ba_code",                   # 2 Billing Authority Code
    "ndr_community_code",        # 3 NDR Community Code
    "ba_reference",              # 4 BA Reference Number
    "description_code",          # 5 Primary and Secondary Description Code
    "description_text",          # 6 Primary Description Text
    "uarn",                      # 7 Unique Address Reference Number
    "full_property_identifier",  # 8 Full Property Identifier
    "firm_name",                 # 9 Firm Name
    "number_or_name",            # 10 Number or Name
    "street",                    # 11 Street
    "town",                      # 12 Town
    "postal_district",           # 13 Postal District
    "county",                    # 14 County
    "postcode",                  # 15 Postcode
    "effective_date",            # 16 Effective Date
    "composite_indicator",       # 17 Composite Indicator
    "rateable_value",            # 18 Rateable Value
    "appeal_settlement_code",    # 19 Appeal Settlement Code
    "assessment_reference",      # 20 Assessment Reference
    "list_alteration_date",      # 21 List Alteration Date
    "scat_code",                 # 22 SCAT Code and Suffix
    "sub_street_3",              # 23 Sub-Street Level 3
    "sub_street_2",              # 24 Sub-Street Level 2
    "sub_street_1",              # 25 Sub-Street Level 1
    "case_number",               # 26 Case Number
    "current_from_date",         # 27 Current From Date
    "current_to_date",           # 28 Current To Date
]

ZIP_PATTERN = re.compile(r"uk-englandwales-ndr-2026-listentries-compiled-epoch-(\d{4})-baseline-csv\.zip$")


def find_zip():
    matches = [(int(m.group(1)), p) for p in RAW.iterdir() if (m := ZIP_PATTERN.search(p.name))]
    if not matches:
        raise SystemExit(
            "No 2026 list entries baseline zip found in data/raw/. Download "
            "uk-englandwales-ndr-2026-listentries-compiled-epoch-NNNN-baseline-csv.zip "
            "from the VOA rating list downloads page after accepting its terms."
        )
    matches.sort()
    if len(matches) > 1:
        log.warning("Several baseline zips found; using the highest epoch: %s", matches[-1][1].name)
    return matches[-1]


def main():
    epoch, zip_path = find_zip()
    log.info("Reading %s (epoch %04d)", zip_path.name, epoch)

    with zipfile.ZipFile(zip_path) as zf:
        members = [i for i in zf.infolist() if i.filename.endswith(".csv") and "historic" not in i.filename]
        if len(members) != 1:
            raise SystemExit(f"Expected one current list entries CSV in the zip, found {[m.filename for m in members]}")
        member = members[0]
        extract_dir = WORK / "_extract"
        shutil.rmtree(extract_dir, ignore_errors=True)
        extract_dir.mkdir()
        csv_path = extract_dir / "list_entries.csv"
        with zf.open(member) as src, open(csv_path, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1 << 24)
    file_date = datetime(*member.date_time)

    con = connect()
    columns = {name: "VARCHAR" for name in VOA_COLUMNS + ["trailing_empty"]}
    columns_sql = "{" + ", ".join(f"'{k}': '{v}'" for k, v in columns.items()) + "}"
    con.execute(f"""
        CREATE TABLE raw AS
        SELECT * FROM read_csv('{sql_path(csv_path)}', delim='*', header=false, quote='', escape='',
                               columns={columns_sql}, auto_detect=false)
    """)
    rows = count(con, "raw")
    stray = con.execute("SELECT count(*) FROM raw WHERE trailing_empty IS NOT NULL").fetchone()[0]
    if stray:
        raise SystemExit(f"{stray} rows have data after field 28; the file layout does not match the specification.")
    with open(csv_path, "rb") as f:
        lines = sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1 << 24), b""))
    if lines != rows:
        raise SystemExit(f"Line count {lines} does not match rows loaded {rows}.")

    out = WORK / "rating_list.parquet"
    con.execute(f"COPY (SELECT * EXCLUDE (trailing_empty) FROM raw) TO '{sql_path(out)}' (FORMAT parquet)")

    latest_current_from = con.execute(
        "SELECT max(strptime(current_from_date, '%d-%b-%Y'))::DATE FROM raw"
    ).fetchone()[0]
    metadata = {
        "source_zip": zip_path.name,
        "source_member": member.filename,
        "epoch": f"{epoch:04d}",
        "file_date": file_date.date().isoformat(),
        "latest_current_from_date": latest_current_from.isoformat(),
        "rows": str(rows),
        "ingested_at": datetime.now().isoformat(timespec="seconds"),
    }
    con.execute("CREATE TABLE metadata (key VARCHAR, value VARCHAR)")
    con.executemany("INSERT INTO metadata VALUES (?, ?)", list(metadata.items()))
    con.execute(f"COPY metadata TO '{sql_path(WORK / 'metadata.parquet')}' (FORMAT parquet)")

    shutil.rmtree(extract_dir, ignore_errors=True)
    log.info("Rows in file: %d. Rows written: %d. Output: %s", rows, rows, out)
    write_stage_log("01_ingest", rows_in=rows, rows_out=rows, **metadata)


if __name__ == "__main__":
    main()
