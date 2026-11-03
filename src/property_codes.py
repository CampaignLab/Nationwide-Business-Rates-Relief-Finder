"""Human-readable VOA code evidence; display only, never eligibility rules."""
import csv
from functools import lru_cache

CODE_FIELDS = ('primary_description_code', 'primary_description',
               'secondary_description', 'scat_category', 'scat_description')
SECONDARY = {'W': 'Workshop and premises', 'S': 'Store and premises',
             'C': 'Car space and premises', 'O': 'Office and premises'}


@lru_cache(maxsize=4)
def labels(mapping_dir):
    with (mapping_dir / 'sector_map.csv').open(encoding='utf-8', newline='') as f:
        primary = {r['primary_description_code']: r['spec_description'] for r in csv.DictReader(f)}
    with (mapping_dir / 'scat_labels.csv').open(encoding='utf-8', newline='') as f:
        scat = {r['scat_code']: r['scat_description'] for r in csv.DictReader(f)}
    return primary, scat


def describe_codes(record, mapping_dir):
    primary_labels, scat_labels = labels(mapping_dir)
    raw = str(record.get('description_code') or '').strip()
    primary, secondary = raw, ''
    # Check complete primary codes first: CS and CC are not secondary suffixes.
    if raw not in primary_labels and raw[:-1] in primary_labels and raw[-1:] in SECONDARY:
        primary, secondary = raw[:-1], raw[-1]
    category = str(record.get('scat_code') or '').strip()[:3]
    return {
        'primary_description_code': primary,
        'primary_description': primary_labels.get(primary, ''),
        'secondary_description': SECONDARY.get(secondary, ''),
        'scat_category': category,
        'scat_description': scat_labels.get(category, ''),
    }
