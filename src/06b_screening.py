"""Add screening, name provenance and official council links without changing legacy eligibility."""
import csv
import json
from collections import Counter
from common import MAPPING, WORK, OUT, CONFIG, connect, sql_path, write_stage_log
from screening import screen_details


def main():
    con=connect()
    con.execute(f"CREATE VIEW original AS SELECT * FROM read_parquet('{sql_path(WORK/'flagged.parquet')}')")
    def lookup(name,key):
        rows=list(csv.DictReader((MAPPING/name).open(encoding='utf-8')))
        assert len(rows)==len({r[key] for r in rows}),f'Duplicate {key} in {name}'
        return {r[key]:r for r in rows}
    names=lookup('researched_names.csv','property_reference')
    councils=lookup('council_links.csv','ba_code')
    warnings=lookup('property_review_evidence.csv','property_reference')
    original_counts=dict(con.execute('SELECT target_new_full_relief,count(*) FROM original GROUP BY 1').fetchall())
    headers=['uarn','screening_outcome','screening_reason','review_reasons','trading_name','name_source','name_recorded_date','name_verification_status','council_url','council_link_source','council_link_checked_date','evidence_source','review_categories','use_review_group','secondary_description_code']
    path=WORK/'_screening.csv'
    cur=con.execute('SELECT * FROM original WHERE rateable_value>12000 AND rateable_value<=18000')
    columns=[d[0] for d in cur.description]
    counts=Counter()
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(headers)
        while batch:=cur.fetchmany(10000):
            for values in batch:
                p=dict(zip(columns,values));ref=p['uarn'];name=names.get(ref,{})
                evidence=warnings.get(ref,{})
                p['evidence_warning']=evidence.get('warning','')
                detail=screen_details(p)
                outcome,reason=detail['screening_outcome'],detail['screening_reason'];counts[outcome]+=1
                council=councils.get(p['ba_code'])
                assert council and council['council_url'].startswith(('https://','http://')),p['ba_code']
                writer.writerow([ref,outcome,reason,reason if outcome=='needs_review' else '',name.get('trading_name',''),name.get('name_source',''),name.get('name_recorded_date',''),name.get('name_verification_status',''),council['council_url'],council['link_source'],council['link_checked_date'],evidence.get('source',''),detail['review_categories'],detail['use_review_group'],detail['secondary_description_code']])
    con.execute(f"CREATE TABLE screening AS SELECT * FROM read_csv('{sql_path(path)}', all_varchar=true)")
    assert con.execute('SELECT count(*)=count(DISTINCT uarn) FROM screening').fetchone()[0]
    con.execute(f"""COPY (SELECT o.*,coalesce(s.screening_outcome,'outside_target') AS screening_outcome,
      coalesce(s.screening_reason,'Outside the target band: rateable value must be above £12,000 and up to £18,000.') AS screening_reason,
      s.* EXCLUDE(uarn,screening_outcome,screening_reason)
      FROM original o LEFT JOIN screening s USING(uarn)) TO '{sql_path(WORK/'screened.parquet')}' (FORMAT parquet)""")
    assert con.execute(f"SELECT count(*) FROM read_parquet('{sql_path(WORK/'screened.parquet')}')").fetchone()[0]==con.execute('SELECT count(*) FROM original').fetchone()[0]
    con.execute(f"CREATE VIEW revised AS SELECT * FROM read_parquet('{sql_path(WORK/'screened.parquet')}')")
    benchmark=lookup('earley_benchmark.csv','property_reference')
    refs=','.join("'"+r+"'" for r in benchmark)
    rows=con.execute(f'SELECT uarn,full_property_identifier,rateable_value,constituency_name,screening_outcome,screening_reason FROM revised WHERE uarn IN ({refs})').fetchall()
    assert len(rows)==len(benchmark),'All comparison assessments must survive'
    with (OUT/'earley_comparison.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['property_reference','address','rateable_value','constituency','screening_outcome','screening_reason','in_previous_live_list','in_independent_spreadsheet'])
        for row in rows:w.writerow([*row,benchmark[row[0]]['in_previous_live_list'],benchmark[row[0]]['in_independent_spreadsheet']])
    assigned=dict(con.execute("SELECT screening_outcome,count(*) FROM revised WHERE constituency_code IS NOT NULL AND screening_outcome<>'outside_target' GROUP BY 1").fetchall())
    unmatched=con.execute("SELECT count(*) FROM revised WHERE constituency_code IS NULL AND screening_outcome='needs_review'").fetchone()[0]
    con.execute(f"COPY (SELECT * FROM revised WHERE constituency_code IS NULL AND screening_outcome='needs_review') TO '{sql_path(OUT/'unassigned_review.csv')}' (HEADER)")
    previous=json.loads((CONFIG/'previous_publication.json').read_text(encoding='utf-8'))
    transitions=con.execute('SELECT target_new_full_relief,screening_outcome,count(*) FROM revised WHERE rateable_value>12000 AND rateable_value<=18000 GROUP BY 1,2 ORDER BY 1,2').fetchall()
    report={'previous_publication':previous,'legacy_model_target_total_after_mapping_changes':original_counts.get(True,0),'target_band_outcomes':dict(counts),'assigned_outcomes':assigned,'unassigned_review':unmatched,'earley_benchmark':dict(Counter(r[4] for r in rows)),'benchmark_records':len(benchmark),'name_records':len(names),'legacy_model_to_screening':[{'legacy_target':r[0],'screening_outcome':r[1],'count':r[2]} for r in transitions], 'mapping_changes':['Marinas and moorings changed from excluded to conditional leisure; unspecified uses require review.','Generic shops separated from clear qualifying uses.','Firm-name matches are review warnings, not confirmed ratepayer matches.']}
    (OUT/'screening_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    write_stage_log('06b_screening',rows_in=con.execute('SELECT count(*) FROM original').fetchone()[0],rows_out=con.execute('SELECT count(*) FROM revised').fetchone()[0],**report)
    print(json.dumps(report,indent=2))
    path.unlink()


if __name__=='__main__':main()
