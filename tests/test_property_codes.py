from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from property_codes import describe_codes

MAPPING = Path(__file__).resolve().parents[1] / 'mapping'


def test_original_codes_and_secondary_are_not_confused():
    result = describe_codes({'description_code': 'CSO', 'scat_code': '249G'}, MAPPING)
    assert result['primary_description_code'] == 'CS'
    assert result['primary_description'] == 'SHOP AND PREMISES'
    assert result['secondary_description'] == 'Office and premises'
    assert result['scat_category'] == '249'
    assert result['scat_description'] == 'Shops'
    for code in ('CS', 'CC'):
        assert describe_codes({'description_code': code}, MAPPING)['secondary_description'] == ''


def test_unknown_codes_remain_visible_without_inventing_labels():
    result = describe_codes({'description_code': 'ZZZ', 'scat_code': '000X'}, MAPPING)
    assert result['primary_description_code'] == 'ZZZ'
    assert result['primary_description'] == ''
    assert result['scat_category'] == '000'
    assert result['scat_description'] == ''
