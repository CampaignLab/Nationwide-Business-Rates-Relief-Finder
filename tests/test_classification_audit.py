import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('classification_audit',ROOT/'scripts/classification_audit.py')
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_effective_rules_explain_overrides_and_ambiguity():
    entries={r['scat_code']:r for r in audit.build_audit(ROOT/'mapping',[('CO','203'),('CR','234')])}
    rule=lambda scat, primary: next(r for r in entries[scat]['rules'] if r['primary_code']==primary)
    assert rule('021','CS')['sector']=='other'  # financial use overrides generic shop
    assert rule('442','CS')['sector']=='hospitality'  # takeaway SCAT overrides retail primary
    assert rule('203','LX')['sector']=='leisure'  # same SCAT, primary-specific override
    assert rule('203','CO')['sector']=='other'
    assert rule('249','CS')['source']=='Primary-code fallback'
    assert 'ambiguous' in rule('249','CS')['flags']
    assert rule('249','*')['sector']=='primary_dependent'
    assert '210' in rule('425','*')['reason'] and 'dispensing' in rule('425','*')['reason']


def test_observed_unknown_codes_are_retained_without_invented_classification():
    entries={r['scat_code']:r for r in audit.build_audit(ROOT/'mapping',[('UNKNOWN','000')])}
    unknown=next(r for r in entries['000']['rules'] if r['primary_code']=='UNKNOWN')
    assert unknown['confidence']=='low'
    assert unknown['sector']=='other'
    assert 'Label not recorded' in entries['000']['scat_description']
