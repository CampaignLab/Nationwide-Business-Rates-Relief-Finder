"""Synthetic end-to-end stage 6 -> parquet -> stage 7 -> CSV/XLSX/index check."""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import duckdb
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def load_stage(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'src' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_postcodes_survive_but_deleted_proxy_does_not(tmp_path,monkeypatch):
    con=duckdb.connect()
    con.execute('CREATE TABLE raw(uarn VARCHAR,ba_code VARCHAR,ba_reference VARCHAR,description_code VARCHAR,description_text VARCHAR,full_property_identifier VARCHAR,postcode VARCHAR,rateable_value VARCHAR)')
    con.executemany('INSERT INTO raw VALUES (?,?,?,?,?,?,?,?)',[
        ('a','0360','1','CR','CAFE','One',None,'15000'),
        ('b','0360','2','CR','CAFE','Two','NOT A POSTCODE','15000'),
        ('c','0360','3','CR','CAFE','Three','RG6 1AA','')])
    con.execute(f"COPY raw TO '{(tmp_path/'rating_list.parquet').as_posix()}' (FORMAT parquet)")
    con.close()
    stage=load_stage('02_clean')
    monkeypatch.setattr(stage,'WORK',tmp_path)
    monkeypatch.setattr(stage,'connect',duckdb.connect)
    monkeypatch.setattr(stage,'write_stage_log',lambda *a,**kw:None)
    stage.main()
    con=duckdb.connect()
    kept=con.execute(f"SELECT uarn,postcode_raw FROM read_parquet('{(tmp_path/'clean.parquet').as_posix()}') ORDER BY uarn").fetchall()
    assert kept==[('a',None),('b','NOT A POSTCODE')]
    assert 'deleted property' in (tmp_path/'rejected_rows.csv').read_text(encoding='utf-8')


def test_only_new_full_relief_targets_reach_published_files(tmp_path, monkeypatch):
    work, out = tmp_path / 'work', tmp_path / 'out'
    work.mkdir()
    out.mkdir()
    con = duckdb.connect()
    con.execute('''CREATE TABLE input (
        uarn VARCHAR, rateable_value INTEGER, sector VARCHAR, is_london BOOLEAN,
        firm_name_normalised VARCHAR, firm_property_count INTEGER, firm_total_rv INTEGER,
        firm_other_max_rv INTEGER, constituency_code VARCHAR, constituency_name VARCHAR,
        region_name VARCHAR, firm_name VARCHAR, full_property_identifier VARCHAR,
        postcode VARCHAR, ba_name VARCHAR)''')
    cases = [(12000,'retail'),(12001,'retail'),(15000,'retail'),(18000,'pub'),
             (18001,'retail'),(16000,'other'),(16000,'possible_vape_shop'),(16000,'retail')]
    for i,(rv,sector) in enumerate(cases):
        multi = i == 7
        con.execute('INSERT INTO input VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    [str(i),rv,sector,False,'chain' if multi else None,2 if multi else 1,
                     19000 if multi else rv,3000 if multi else 0,'E14001196','Test seat',
                     'Test region','Chain' if multi else None,f'{i} Example Street','ZZ1 1ZZ','Test council'])
    con.execute("ALTER TABLE input ADD COLUMN description_text VARCHAR DEFAULT 'SHOP AND PREMISES'")
    con.execute("UPDATE input SET description_text='PUB AND PREMISES' WHERE sector='pub'")
    con.execute("ALTER TABLE input ADD COLUMN description_code VARCHAR DEFAULT 'CS'")
    con.execute("ALTER TABLE input ADD COLUMN scat_code VARCHAR DEFAULT '249G'")
    con.execute("ALTER TABLE input ADD COLUMN sector_confidence VARCHAR DEFAULT 'high'")
    con.execute("ALTER TABLE input ADD COLUMN ba_code VARCHAR DEFAULT '0360'")
    con.execute(f"COPY input TO '{(work / 'occupiers.parquet').as_posix()}' (FORMAT parquet)")
    con.execute('CREATE TABLE meta(key VARCHAR, value VARCHAR)')
    con.executemany('INSERT INTO meta VALUES (?,?)', [('epoch','test'),('source_zip','synthetic.zip'),
                    ('file_date','2026-11-03'),('latest_current_from_date','2026-11-03')])
    con.execute(f"COPY meta TO '{(work / 'metadata.parquet').as_posix()}' (FORMAT parquet)")
    con.close()

    s6 = load_stage('06_eligibility')
    monkeypatch.setattr(s6,'WORK',work)
    monkeypatch.setattr(s6,'connect',duckdb.connect)
    monkeypatch.setattr(s6,'write_stage_log',lambda *a,**kw: None)
    s6.main()
    mappings=tmp_path/'mapping';mappings.mkdir()
    for name in ['researched_names.csv','council_links.csv','property_review_evidence.csv']:
        (mappings/name).write_text((ROOT/'mapping'/name).read_text(encoding='utf-8'),encoding='utf-8')
    (mappings/'earley_benchmark.csv').write_text('property_reference,in_previous_live_list,in_independent_spreadsheet\n1,True,True\n',encoding='utf-8')
    screening=load_stage('06b_screening')
    for key,value in [('WORK',work),('OUT',out),('MAPPING',mappings),('connect',duckdb.connect),('write_stage_log',lambda *a,**kw:None)]:
        monkeypatch.setattr(screening,key,value)
    screening.main()
    s7 = load_stage('07_publish')
    monkeypatch.setattr(s7,'WORK',work)
    monkeypatch.setattr(s7,'OUT',out)
    monkeypatch.setattr(s7,'connect',duckdb.connect)
    monkeypatch.setattr(s7,'read_stage_log',lambda *a: {'onspd_release':'ONSPD_AUG_2026'})
    monkeypatch.setattr(s7,'write_stage_log',lambda *a,**kw: None)
    # Reporting requires the earlier real-data stages; keep those outside this fixture.
    monkeypatch.setattr(s7,'write_report',lambda *a: None)
    monkeypatch.setattr(s7.validation,'earley',lambda con: ('',{}))
    monkeypatch.setattr(s7.validation,'plausibility',lambda con: ('',{}))
    monkeypatch.setattr(s7.validation,'spot_check',lambda con: '')
    s7.main()
    index = json.loads((out / 'constituency_index.json').read_text(encoding='utf-8'))
    assert index['cohort']['lower_rv_exclusive'] == 12000
    assert index['cohort']['upper_rv_inclusive'] == 18000
    seat = index['constituencies'][0]
    assert seat['counts']['properties_in_list'] == 8
    assert seat['counts']['target_new_full_relief'] == 5
    assert seat['counts']['likely_candidate'] == 1
    assert seat['counts']['needs_review'] == 4
    assert seat['counts']['now_possibly_eligible_now'] == 1
    assert seat['counts']['now_not_flagged'] == 4
    with open(out / seat['files']['csv'],encoding='utf-8-sig',newline='') as f:
        rows = list(csv.reader(f))
    start = next(i for i,row in enumerate(rows) if 'property_reference' in row)
    records = [dict(zip(rows[start],r)) for r in rows[start+1:]]
    assert {int(r['rateable_value']) for r in records} == {12001,15000,16000,18000}
    assert len({r['property_reference'] for r in records})==5
    assert all(r['scat_category']=='249' and r['scat_description']=='Shops' for r in records)
    assert all(r['primary_description_code']=='CS' and r['secondary_description']=='' for r in records)
    assert next(r for r in records if r['property_reference']=='7')['screening_outcome']=='needs_review'
    assert next(r for r in records if r['property_reference']=='7')['target_new_full_relief']=='False'
    wb = load_workbook(out / seat['files']['xlsx'],read_only=True)
    assert len(list(wb['Properties'].values)) == 6
    wb.close()
