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
    assert seat['counts']['target_new_full_relief'] == 3
    assert seat['counts']['now_possibly_eligible_now'] == 1
    assert seat['counts']['now_not_flagged'] == 2
    with open(out / seat['files']['csv'],encoding='utf-8-sig',newline='') as f:
        rows = list(csv.reader(f))
    start = next(i for i,row in enumerate(rows) if 'property_reference' in row)
    records = [dict(zip(rows[start],r)) for r in rows[start+1:]]
    assert {int(r['rateable_value']) for r in records} == {12001,15000,18000}
    assert all(r['target_new_full_relief'] == 'True' for r in records)
    assert all(float(r['relief_from_apr_2027']) == 1 for r in records)
    wb = load_workbook(out / seat['files']['xlsx'],read_only=True)
    assert len(list(wb['Properties'].values)) == 4
    wb.close()
