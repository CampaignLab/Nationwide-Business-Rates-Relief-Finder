"""Stage 6: apply the screening rules from config/rules.yaml to every English property."""
import csv
from functools import lru_cache

from common import WORK, connect, count, get_logger, load_rules, sql_path, write_stage_log
from eligibility import Property, assess

log = get_logger("06_eligibility")


def main():
    rules = load_rules()
    log.info("Rules: %s", rules["snapshot_note"])

    @lru_cache(maxsize=None)
    def cached(*args):
        return assess(Property(*args), rules)

    con = connect()
    con.execute(f"CREATE VIEW src AS SELECT * FROM read_parquet('{sql_path(WORK / 'occupiers.parquet')}')")
    rows_in = count(con, "src")
    if con.execute("SELECT count(*) - count(DISTINCT uarn) FROM src").fetchone()[0]:
        raise SystemExit("UARN is not unique; results cannot be joined back safely.")

    results_csv = WORK / "_eligibility_results.csv"
    cur = con.execute("""
        SELECT uarn, rateable_value, sector, is_london, firm_name_normalised IS NOT NULL,
               firm_property_count, firm_total_rv, firm_other_max_rv
        FROM src
    """)
    with open(results_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["uarn", "status_now", "status_from_apr_2027", "reason", "relief_now", "relief_from_apr_2027"])
        while batch := cur.fetchmany(100_000):
            for uarn, *args in batch:
                r = cached(*args)
                w.writerow([uarn, r.status_now, r.status_from_apr_2027, r.reason,
                            round(r.relief_now, 4), round(r.relief_from_apr_2027, 4)])

    con.execute(f"""
        CREATE TABLE results AS SELECT * FROM read_csv('{sql_path(results_csv)}', header=true,
            types={{'uarn': 'VARCHAR', 'relief_now': 'DOUBLE', 'relief_from_apr_2027': 'DOUBLE'}})
    """)
    con.execute(f"""
        COPY (SELECT s.*, r.* EXCLUDE (uarn) FROM src s JOIN results r USING (uarn))
        TO '{sql_path(WORK / 'flagged.parquet')}' (FORMAT parquet)
    """)
    results_csv.unlink()
    rows_out = con.execute(f"SELECT count(*) FROM read_parquet('{sql_path(WORK / 'flagged.parquet')}')").fetchone()[0]
    assert rows_out == rows_in

    by_now = dict(con.execute("SELECT status_now, count(*) FROM results GROUP BY 1 ORDER BY 1").fetchall())
    by_27 = dict(con.execute("SELECT status_from_apr_2027, count(*) FROM results GROUP BY 1 ORDER BY 1").fetchall())
    either = con.execute("""SELECT count(*) FROM results
                            WHERE status_now <> 'not_flagged' OR status_from_apr_2027 <> 'not_flagged'""").fetchone()[0]
    log.info("Rows in: %d. Rows out: %d. Flagged under either view: %d", rows_in, rows_out, either)
    log.info("status_now: %s", by_now)
    log.info("status_from_apr_2027: %s", by_27)
    log.info("Distinct input combinations assessed: %d", cached.cache_info().currsize)
    write_stage_log("06_eligibility", rows_in=rows_in, rows_out=rows_out, flagged_either=either,
                    status_now=by_now, status_from_apr_2027=by_27, rules_snapshot=rules["snapshot_note"])


if __name__ == "__main__":
    main()
