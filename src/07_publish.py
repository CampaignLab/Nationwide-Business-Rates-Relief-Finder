"""Stage 7: write per-constituency files, the national summary, the index and the run report."""
import csv
import json
import re
import shutil
from datetime import date

from openpyxl import Workbook

import validation
from common import MAPPING, OUT, WORK, connect, get_logger, load_rules, read_stage_log, sql_path, write_stage_log

log = get_logger("07_publish")

VOA_TERMS_URL = "https://www.tax.service.gov.uk/view-my-valuation/terms-and-conditions"
DISCLAIMER = ("This list shows properties that may be eligible for relief based on rateable value and property type. "
              "It does not show who pays business rates or who receives relief. Check eligibility with the billing "
              "authority before contacting a business.")

OUTPUT_COLUMNS = [
    ("constituency_code", "constituency_code"),
    ("constituency_name", "constituency_name"),
    ("property_reference", "uarn"),
    ("firm_name", "firm_name"),
    ("address", "full_property_identifier"),
    ("postcode", "postcode"),
    ("billing_authority", "ba_name"),
    ("is_london", "is_london"),
    ("rateable_value", "rateable_value"),
    ("sector", "sector"),
    ("firm_property_count", "firm_property_count"),
    ("status_now", "status_now"),
    ("status_from_apr_2027", "status_from_apr_2027"),
    ("relief_now", "relief_now"),
    ("relief_from_apr_2027", "relief_from_apr_2027"),
    ("target_new_full_relief", "target_new_full_relief"),
    ("reason", "reason"),
    ("snapshot_epoch", "snapshot_epoch"),
    ("verified_with_council", "verified_with_council"),
]
STATUSES_NOW = ["likely_eligible_now", "possibly_eligible_now", "not_flagged"]
STATUSES_2027 = ["likely_eligible_now", "possibly_eligible_now", "eligible_from_apr_2027",
                 "excluded_possible_vape_shop", "not_flagged"]


def file_stem(code: str, name: str) -> str:
    return f"{code}_{re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_')}"


def notice_lines(meta: dict, rules: dict, mapping_reviewed: bool, onspd_year: str) -> list[str]:
    lines = [
        "NOTICE",
        f"Status: potentially eligible only. {DISCLAIMER}",
        ("Licence: contains Valuation Office (VO) rating list data, Crown copyright and database right. It is supplied "
         "under the VO's restricted licence, not the Open Government Licence. Use is limited to non-domestic rating "
         f"purposes and onward disclosure is restricted. The VO terms apply to anyone who receives this file: {VOA_TERMS_URL}"),
        ("Do not distribute: this file is for authorised users only. It may contain personal data (sole traders and "
         "home addresses). Do not share it further until the VO has confirmed the use is within its licence and data "
         "protection advice has been taken."),
        (f"Snapshot: VOA 2026 rating list, compiled epoch {meta['epoch']} baseline ({meta['source_zip']}), "
         f"file dated {meta['file_date']}, latest record date {meta['latest_current_from_date']}."),
        f"Rules: {rules['snapshot_note']}",
        (f"Selection: RHL properties with rateable value above £{rules['sbrr_general']['full_relief_max_rv']:,} "
         f"and up to £{rules['sbrr_rhl_from_april_2027']['full_relief_max_rv']:,} inclusive, potentially moving "
         "to full relief from 1 April 2027, subject to other eligibility conditions. These are property records, not unique businesses."),
        (f"Contains OS data © Crown copyright and database right {onspd_year}. Contains Royal Mail data © Royal Mail "
         f"copyright and database right {onspd_year}. Source: Office for National Statistics licensed under the Open "
         "Government Licence v.3.0."),
    ]
    if not mapping_reviewed:
        lines.append("Sector mapping: draft, awaiting human review. Sector and April 2027 statuses may change after review.")
    lines.append(f"Generated: {date.today().isoformat()}")
    return lines


def write_constituency(code, name, rows, notice, csv_dir, xlsx_dir):
    stem = file_stem(code, name)
    headers = [h for h, _ in OUTPUT_COLUMNS]
    with open(csv_dir / f"{stem}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        for line in notice:
            w.writerow([line])
        w.writerow([])
        w.writerow(headers)
        w.writerows(rows)
    wb = Workbook(write_only=True)
    ws_notice = wb.create_sheet("Notice")
    for line in notice:
        ws_notice.append([line])
    ws = wb.create_sheet("Properties")
    ws.append(headers)
    for r in rows:
        ws.append(list(r))
    wb.save(xlsx_dir / f"{stem}.xlsx")
    return f"{stem}.csv", f"{stem}.xlsx"


def mapping_review_state() -> dict:
    state = {}
    for name in ("sector_map.csv", "scat_overrides.csv", "text_flags.csv"):
        with open(MAPPING / name, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        state[name] = {"rows": len(rows), "awaiting_review": sum(r["review_status"] != "signed_off" for r in rows)}
    return state


def main():
    rules = load_rules()
    con = connect()
    meta = dict(con.execute(f"SELECT key, value FROM read_parquet('{sql_path(WORK / 'metadata.parquet')}')").fetchall())
    review = mapping_review_state()
    mapping_reviewed = all(v["awaiting_review"] == 0 for v in review.values())
    if not mapping_reviewed:
        log.warning("Sector mapping is awaiting human review: %s", review)
    onspd_year = re.search(r"(\d{4})", read_stage_log("03_constituency")["onspd_release"]).group(1)
    notice = notice_lines(meta, rules, mapping_reviewed, onspd_year)

    con.execute(f"""
        CREATE TABLE flagged AS
        SELECT *, '{meta['epoch']}' AS snapshot_epoch, NULL::VARCHAR AS verified_with_council
        FROM read_parquet('{sql_path(WORK / 'flagged.parquet')}')
    """)
    rows_in = con.execute("SELECT count(*) FROM flagged").fetchone()[0]
    # Publish only the user's target cohort, not all existing/tapered SBRR cases.
    flag_cond = "target_new_full_relief = true"

    csv_dir, xlsx_dir = OUT / "constituencies" / "csv", OUT / "constituencies" / "xlsx"
    shutil.rmtree(OUT / "constituencies", ignore_errors=True)
    csv_dir.mkdir(parents=True)
    xlsx_dir.mkdir(parents=True)

    select = ", ".join(src for _, src in OUTPUT_COLUMNS)
    cur = con.execute(f"""
        SELECT {select} FROM flagged
        WHERE constituency_code IS NOT NULL AND {flag_cond}
        ORDER BY constituency_code, postcode, full_property_identifier, uarn
    """)
    files, current, buffer, written = {}, None, [], 0

    def flush():
        nonlocal written
        if current:
            files[current[0]] = write_constituency(current[0], current[1], buffer, notice, csv_dir, xlsx_dir)
            written += len(buffer)

    while batch := cur.fetchmany(50_000):
        for row in batch:
            key = (row[0], row[1])
            if key != current:
                flush()
                current, buffer = key, []
            buffer.append(row)
    flush()
    log.info("Wrote %d constituency files (CSV and XLSX) with %d rows", len(files), written)

    # National summary.
    now_cols = ", ".join(f"count(*) FILTER (WHERE {flag_cond} AND status_now = '{s}') AS now_{s}" for s in STATUSES_NOW)
    apr_cols = ", ".join(f"count(*) FILTER (WHERE {flag_cond} AND status_from_apr_2027 = '{s}') AS apr2027_{s}" for s in STATUSES_2027)
    summary = con.execute(f"""
        SELECT coalesce(constituency_code, '') AS constituency_code,
               coalesce(constituency_name, '(no constituency: postcode not matched or outside England)') AS constituency_name,
               coalesce(any_value(region_name), '') AS region_name,
               count(*) AS properties_in_list,
               count(*) FILTER (WHERE {flag_cond}) AS target_new_full_relief,
               {now_cols}, {apr_cols}
        FROM flagged GROUP BY constituency_code, constituency_name
        ORDER BY constituency_code IS NULL, constituency_code
    """)
    headers = [d[0] for d in summary.description]
    summary_rows = summary.fetchall()
    with open(OUT / "national_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(summary_rows)

    english_constituencies = con.execute("SELECT count(DISTINCT constituency_code) FROM flagged WHERE constituency_code LIKE 'E14%'").fetchone()[0]
    with_flags = sum(1 for r in summary_rows if r[0] and r[4] > 0)
    missing_files = [r[0] for r in summary_rows if r[0] and r[4] > 0 and r[0] not in files]
    if missing_files:
        raise SystemExit(f"Constituencies with flagged properties but no file: {missing_files}")

    index = {
        "cohort": {
            "id": "rhl_new_full_relief",
            "lower_rv_exclusive": rules["sbrr_general"]["full_relief_max_rv"],
            "upper_rv_inclusive": rules["sbrr_rhl_from_april_2027"]["full_relief_max_rv"],
            "effective_from": rules["sbrr_rhl_from_april_2027"]["effective_from"],
        },
        "snapshot_epoch": meta["epoch"],
        "source_file": meta["source_zip"],
        "file_date": meta["file_date"],
        "rules_snapshot": rules["snapshot_note"],
        "sector_mapping_reviewed": mapping_reviewed,
        "notice": DISCLAIMER,
        "licence": f"VO restricted licence: {VOA_TERMS_URL}",
        "constituencies": [
            {
                "code": r[0], "name": r[1], "region": r[2],
                "counts": dict(zip(headers[3:], r[3:])),
                "files": {"csv": f"constituencies/csv/{files[r[0]][0]}", "xlsx": f"constituencies/xlsx/{files[r[0]][1]}"},
            }
            for r in summary_rows if r[0] in files
        ],
    }
    with open(OUT / "constituency_index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    # Run report.
    earley_md, earley_data = validation.earley(con)
    plaus_md, plaus_data = validation.plausibility(con)
    spot_md = validation.spot_check(con)
    write_stage_log("07_publish", rows_in=rows_in, rows_out=written, constituency_files=len(files),
                    english_constituencies_in_data=english_constituencies, constituencies_with_flags=with_flags,
                    earley=earley_data, plausibility=plaus_data, mapping_review=review)
    write_report(meta, rules, review, english_constituencies, len(files), earley_md, plaus_md, spot_md, con)
    log.info("Rows in: %d. Rows written to constituency files: %d", rows_in, written)


def write_report(meta, rules, review, english_constituencies, n_files, earley_md, plaus_md, spot_md, con):
    stages = ["01_ingest", "02_clean", "03_constituency", "04_sector", "05_occupiers", "06_eligibility", "07_publish"]
    logs = {s: read_stage_log(s) for s in stages}
    stage_rows = [(s, logs[s]["rows_in"], logs[s]["rows_out"]) for s in stages]
    try:
        tests = read_stage_log("tests")
        tests_line = f"{tests['result']} ({tests['summary']}), run {tests['run_at']}"
    except FileNotFoundError:
        tests_line = "not run in this pipeline run (use run_all.py)"

    c = logs["02_clean"]
    m = logs["03_constituency"]
    welsh_raw = con.execute(f"""SELECT count(*) FROM read_parquet('{sql_path(WORK / 'rating_list.parquet')}')
                                WHERE ba_code BETWEEN '6805' AND '6955'""").fetchone()[0]
    unmatched_top = con.execute(f"""SELECT postcode, properties, ba_name, district_in_onspd
                                    FROM read_csv('{sql_path(WORK / 'unmatched_postcodes.csv')}') LIMIT 10""").fetchall()
    unmatched_pattern = con.execute(f"""
        SELECT sum(properties) FILTER (WHERE regexp_matches(postcode, ' [0-9](ZZ|XX)$')),
               sum(properties) FILTER (WHERE NOT district_in_onspd)
        FROM read_csv('{sql_path(WORK / 'unmatched_postcodes.csv')}')""").fetchone()
    s6 = logs["06_eligibility"]
    t = validation.md_table

    report = f"""# Run report

Generated {date.today().isoformat()}. VOA 2026 list, compiled epoch {meta['epoch']} baseline
(`{meta['source_zip']}`, file dated {meta['file_date']}, latest record date {meta['latest_current_from_date']}).
ONSPD release: `{m['onspd_release']}`. Rules: {rules['snapshot_note']}

This report contains VOA data and is covered by the VO restricted licence. Do not publish it.

## Status of this run

- Unit tests: {tests_line}
- Sector mapping: {"signed off" if all(v['awaiting_review'] == 0 for v in review.values()) else "**awaiting human review**"}
  ({", ".join(f"{k}: {v['awaiting_review']} of {v['rows']} rows awaiting review" for k, v in review.items())})
- Constituency files written: {n_files:,} of {english_constituencies:,} English constituencies present in the data

## Row counts by stage

{t(["Stage", "Rows in", "Rows out"], stage_rows)}

Stage 3 keeps only properties in English billing authorities. Stage 7 "rows out" is the number of target RHL properties
written to constituency files: above the old full-relief threshold, up to and including the new full-relief
threshold, passing the modelled 2027 checks and with a constituency. These are properties, not unique businesses.

## Rejected rows (stage 2)

{t(["Reason", "Rows"], list(c['rejected_by_reason'].items()))}

Total rejected: {c['rejected']:,}, listed in `data/work/rejected_rows.csv`. The VOA specification says rows
with a blank rateable value are proxy records for deleted properties. A further {c['zero_rateable_value']:,} rows
have a rateable value of £0; they are kept but never flagged.

## Wales

Rows with a Welsh billing authority code (6805 to 6955, VOA specification Appendix 1): {welsh_raw:,} in the
raw file, {m['welsh_billing_authority_rows_excluded']:,} after stage 2 rejections. All are excluded.
{m['welsh_billing_authority_rows_with_english_postcode']:,} Welsh billing authority rows have a postcode that
ONSPD places in England; they are still excluded, because the billing authority decides which rules apply.

## Constituency match rate

- English billing authority rows: {m['english_billing_authority_rows']:,}
- Matched to an ONSPD postcode: {m['matched']:,} ({m['match_rate']:.2%}), of which {m['matched_to_terminated_postcode']:,} matched a terminated postcode (ONSPD keeps their geography)
- Unmatched: {m['unmatched']:,}
- Matched but ONSPD places the postcode outside England: {m['matched_but_onspd_country_not_england']:,} {m['matched_but_onspd_country_not_england_by_country']} (kept, with no constituency)
- Rows with an English constituency: {m['rows_with_english_constituency']:,} ({m['constituency_rate']:.2%})

The match rate is {"above" if m['match_rate'] >= 0.99 else "**below**"} 99%. Of the unmatched rows, {unmatched_pattern[0] or 0:,} use postcodes ending in ZZ or XX,
which are usually placeholders rather than real postcodes, and {unmatched_pattern[1] or 0:,} have a postcode district
that does not exist in ONSPD. The rest are in known districts but do not match a live or terminated postcode,
which suggests recording errors in the list. The full list is in `data/work/unmatched_postcodes.csv`.
Largest unmatched postcodes:

{t(["Postcode", "Properties", "Billing authority", "District in ONSPD"], unmatched_top)}

## London

London is identified by billing authority (the 33 London billing authorities, codes 5030 to 5990), because the
aggregate limit depends on the council that bills the property. As a cross-check against the ONSPD region:
{m['london_ba_but_onspd_region_not_london']:,} rows billed by a London authority have a postcode outside the London
region, and {m['onspd_region_london_but_ba_not_london']:,} rows in the London region are billed by a non-London authority.

## Eligibility results (England)

{t(["Status now", "Rows"], list(s6['status_now'].items()))}

{t(["Status from April 2027", "Rows"], list(s6['status_from_apr_2027'].items()))}

Flagged under either status: {s6['flagged_either']:,}.

{earley_md}
{plaus_md}
{spot_md}
"""
    with open(OUT / "run_report.md", "w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    main()
