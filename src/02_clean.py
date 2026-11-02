"""Stage 2: normalise postcodes, cast rateable value, and set aside unusable rows.

Rows with no postcode or no rateable value go to data/work/rejected_rows.csv
with a reason. The VOA specification says rows with a blank rateable value
(item 18) are proxy records for properties deleted from the list, not list entries.
"""
from common import WORK, connect, count, get_logger, sql_path, write_stage_log

log = get_logger("02_clean")

POSTCODE_FORMAT = r"^[A-Z]{1,2}[0-9][0-9A-Z]? [0-9][A-Z]{2}$"


def main():
    con = connect()
    con.execute(f"CREATE VIEW src AS SELECT * FROM read_parquet('{sql_path(WORK / 'rating_list.parquet')}')")
    rows_in = count(con, "src")

    con.execute(f"""
        CREATE TABLE staged AS
        WITH n AS (
            SELECT *,
                   nullif(regexp_replace(upper(coalesce(postcode, '')), '\\s+', '', 'g'), '') AS pc_compact,
                   trim(rateable_value) AS rv_text
            FROM src
        )
        SELECT * EXCLUDE (pc_compact, rv_text, postcode, rateable_value),
               postcode AS postcode_raw,
               rateable_value AS rateable_value_raw,
               CASE WHEN length(pc_compact) BETWEEN 5 AND 7
                    THEN left(pc_compact, length(pc_compact) - 3) || ' ' || right(pc_compact, 3) END AS postcode,
               try_cast(rv_text AS BIGINT) AS rateable_value,
               concat_ws('; ',
                   CASE WHEN pc_compact IS NULL THEN 'postcode missing' END,
                   CASE WHEN pc_compact IS NOT NULL
                         AND NOT regexp_matches(coalesce(CASE WHEN length(pc_compact) BETWEEN 5 AND 7
                              THEN left(pc_compact, length(pc_compact) - 3) || ' ' || right(pc_compact, 3) END, ''),
                              '{POSTCODE_FORMAT}')
                        THEN 'postcode not in a valid UK format' END,
                   CASE WHEN rv_text IS NULL OR rv_text = ''
                        THEN 'rateable value missing (VOA proxy record for a deleted property)' END,
                   CASE WHEN rv_text <> '' AND try_cast(rv_text AS BIGINT) IS NULL
                        THEN 'rateable value not a whole number' END
               ) AS reject_reason
        FROM n
    """)

    con.execute(f"""
        COPY (SELECT reject_reason, uarn, ba_code, ba_reference, description_code, description_text,
                     full_property_identifier, postcode_raw, rateable_value_raw
              FROM staged WHERE reject_reason <> '' ORDER BY reject_reason, ba_code, uarn)
        TO '{sql_path(WORK / 'rejected_rows.csv')}' (HEADER)
    """)
    con.execute(f"""
        COPY (SELECT * EXCLUDE (reject_reason, postcode_raw, rateable_value_raw) FROM staged WHERE reject_reason = '')
        TO '{sql_path(WORK / 'clean.parquet')}' (FORMAT parquet)
    """)

    reasons = dict(con.execute(
        "SELECT reject_reason, count(*) FROM staged WHERE reject_reason <> '' GROUP BY 1 ORDER BY 2 DESC"
    ).fetchall())
    rejected = sum(reasons.values())
    rows_out = con.execute("SELECT count(*) FROM staged WHERE reject_reason = ''").fetchone()[0]
    assert rows_out + rejected == rows_in
    zero_rv = con.execute("SELECT count(*) FROM staged WHERE reject_reason = '' AND rateable_value = 0").fetchone()[0]

    log.info("Rows in: %d. Rows out: %d. Rejected: %d", rows_in, rows_out, rejected)
    for reason, n in reasons.items():
        log.info("  rejected, %s: %d", reason, n)
    log.info("Rows kept with a rateable value of 0: %d", zero_rv)
    write_stage_log("02_clean", rows_in=rows_in, rows_out=rows_out, rejected=rejected,
                    rejected_by_reason=reasons, zero_rateable_value=zero_rv)


if __name__ == "__main__":
    main()
