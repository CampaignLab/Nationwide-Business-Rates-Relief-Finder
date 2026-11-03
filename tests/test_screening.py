import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'src'))
from screening import screen

def property(**changes):
    return dict(rateable_value=15000,sector='hospitality',sector_confidence='high',description_text='CAFE AND PREMISES',constituency_code='E14001210',**changes)

@pytest.mark.parametrize('rv,expected',[(12000,'outside_target'),(12001,'likely_candidate'),(18000,'likely_candidate'),(18001,'outside_target')])
def test_boundaries(rv,expected):
    p=property();p['rateable_value']=rv
    assert screen(p)[0]==expected

@pytest.mark.parametrize('changes,expected',[
    ({'firm_name':None},'likely_candidate'),
    ({'firm_property_count':2,'firm_name':'BOWLING CLUB'},'needs_review'),
    ({'constituency_code':None},'needs_review'),
    ({'sector':'retail','description_text':'SHOP AND PREMISES'},'needs_review'),
    ({'sector':'hospitality','description_text':'SHOP AND PREMISES'},'needs_review'),
    ({'sector':'retail','description_text':'HAIRDRESSING SALON'},'likely_candidate'),
    ({'sector':'retail','description_text':'SHOP','trading_name':'Hair salon'},'needs_review'),
    ({'sector':'retail','firm_name':'Example Estate Agents'},'needs_review'),
    ({'sector':'retail','description_text':'ESTATE AGENCY OFFICE'},'outside_target'),
    ({'sector':'retail','description_text':'POST OFFICE AND PREMISES'},'likely_candidate'),
    ({'sector':'possible_vape_shop'},'needs_review'),
    ({'sector':'possible_adult_gaming_centre'},'needs_review'),
    ({'sector':'other','description_text':'MARINA AND PREMISES'},'needs_review'),
    ({'sector':'other','description_text':'RECREATIONAL MARINA'},'likely_candidate'),
    ({'sector':'other','description_text':'STORE AND PREMISES'},'needs_review'),
    ({'sector':'other','description_text':'FACTORY'},'outside_target'),
    ({'sector':'other','description_text':'SITE OFFICES AND PREMISES'},'outside_target'),
    ({'postcode_terminated':True},'needs_review'),
    ({'evidence_warning':'Identified estate agency in comparison'},'needs_review'),
])
def test_conservative_screening(changes,expected):
    p=property();p.update(changes)
    outcome,reason=screen(p)
    assert outcome==expected
    assert reason
