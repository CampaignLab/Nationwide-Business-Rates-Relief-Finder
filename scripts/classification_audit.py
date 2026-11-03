"""Generate transparent SCAT documentation from the classifier's mapping tables."""
import csv
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from screening import SPECIFIC_SCAT


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def build_audit(mapping, observed=()):
    primary = {r['primary_description_code']: r for r in read(mapping / 'sector_map.csv')}
    overrides = {(r['primary_description_code'], r['scat_code']): r for r in read(mapping / 'scat_overrides.csv')}
    names = {r['scat_code']: r['scat_description'] for r in read(mapping / 'scat_labels.csv')}
    pairs = {(code, scat) for code, row in primary.items() for scat in row['spec_scat_codes'].split(';') if scat}
    pairs.update((code, scat) for code, scat in overrides if code != '*')
    pairs.update((code or '', scat) for code, scat in observed if scat)
    codes = set(names) | {scat for _, scat in pairs} | {scat for _, scat in overrides}
    result = []
    for scat in sorted(codes):
        rules = []
        for code in ['*', *sorted(code for code, category in pairs if category == scat)]:
            row = overrides.get((code, scat)) if code != '*' else None
            source = 'Primary + SCAT override'
            if row is None:
                row = overrides.get(('*', scat))
                source = 'SCAT override (all primary codes)'
            if row is None:
                row = primary.get(code)
                source = 'Primary-code fallback'
            if row is None:
                sector, confidence, status = ('primary_dependent', 'not_assessed', 'not_assessed') if code == '*' else ('other', 'low', 'not_assessed')
                reason = 'No SCAT-only rule. The primary code supplies the sector; unknown primary codes default to other/low. See primary-code download.' if code == '*' else 'Unrecognised primary code with no applicable SCAT override: defaults to other with low mapping confidence.'
            else:
                sector, confidence, status = row['sector'], row['confidence'], row['review_status']
                reason = row['notes'].strip() or ('No qualifying RHL purpose assigned by this primary mapping; this is not a determination of legal exclusion.' if sector == 'other' else 'Inherits the mapped use of the primary description: ' + primary.get(code, {}).get('spec_description', code) + '.')
                # Resolve terse notes such as "As CA" using the referenced rule.
                for ref, parent in primary.items():
                    if reason.startswith('As ' + ref + '.') and parent['notes'].strip():
                        reason += ' Referenced rationale: ' + parent['notes'].strip()
                        break
                for (parent_code, parent_scat), parent in overrides.items():
                    if reason.startswith('As ' + parent_scat + '.') and parent['notes'].strip():
                        reason += ' Referenced rationale: ' + parent['notes'].strip()
                        break
            flags = {sector if sector in {'retail', 'hospitality', 'leisure', 'pub'} else 'outside'}
            if sector in {'primary_dependent', 'possible_vape_shop', 'possible_adult_gaming_centre'} or confidence != 'high' or scat in {'249','268','236','143','189','164'}:
                flags.add('ambiguous')
            if sector == 'primary_dependent':
                flags.discard('outside')
            guidance = 'Sector mapping is an input, not the final screening outcome. Description, location, ratepayer and evidence checks still apply.'
            if scat in SPECIFIC_SCAT:
                guidance += ' This SCAT can resolve generic shop wording when the mapped sector is RHL; it does not override uncertainty or conflicts.'
            if scat == '249':
                guidance += ' Generic shops can include estate agents. Generic wording remains a possible candidate; a specific qualifying description can resolve it.'
            if sector == 'other':
                guidance += ' Conditional-use/text exceptions can retain a property as a possible candidate; other does not automatically mean legally excluded.'
            rules.append(dict(primary_code=code, primary_description=primary.get(code, {}).get('spec_description', 'Any other / unlisted primary code' if code == '*' else 'Unmapped primary code'), sector=sector, confidence=confidence, reason=reason, source=source, review_status=status, screening_guidance=guidance, flags=sorted(flags)))
        result.append(dict(scat_code=scat, scat_description=names.get(scat) or next((r['spec_scat_description'] for (p, s), r in overrides.items() if s == scat), 'Label not recorded in our reference table'), rules=rules))
    return result


def main():
    import duckdb
    observed_path = ROOT / 'data/work/sectored.parquet'
    observed = duckdb.connect().execute('SELECT DISTINCT primary_description_code, left(scat_code,3) FROM read_parquet(?)', [str(observed_path)]).fetchall() if observed_path.exists() else []
    entries = build_audit(ROOT / 'mapping', observed)
    target = ROOT / 'web/dataset'
    target.mkdir(parents=True, exist_ok=True)
    payload = dict(scope='All SCAT codes in our reference/mapping tables and observed VOA snapshot. This is our draft interpretation, not an official relief eligibility table.', precedence='Text flags > primary+SCAT override > wildcard SCAT override > primary-code fallback. Subsequent screening checks can change the result.', codes=entries, text_flags=read(ROOT / 'mapping/text_flags.csv'))
    (target / 'scat_classifications.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    headers = ['scat_code','scat_description','primary_code','primary_description','sector','confidence','reason','source','review_status','screening_guidance']
    with (target / 'scat_classifications.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore'); writer.writeheader()
        for entry in entries:
            for rule in entry['rules']:
                writer.writerow({**entry, **rule})
    (target / 'primary_classifications.csv').write_bytes((ROOT / 'mapping/sector_map.csv').read_bytes())
    # Preserve the supplements when prepare-data stages a freshly rebuilt out folder.
    if (ROOT / 'out').exists():
        for name in ('scat_classifications.csv', 'scat_classifications.json', 'primary_classifications.csv'):
            (ROOT / 'out' / name).write_bytes((target / name).read_bytes())
    esc = lambda value: html.escape(str(value), quote=True)
    rows = []
    for entry in entries:
        flags = sorted({f for rule in entry['rules'] for f in rule['flags']})
        sectors = sorted({r['sector'].replace('_', ' ') for r in entry['rules'] if r['sector'] != 'primary_dependent'})
        details = []
        for rule in entry['rules']:
            details.append('<li><strong>' + esc(rule['primary_code'] + ' — ' + rule['primary_description']) + '</strong><p>Mapped sector: ' + esc(rule['sector'].replace('_', ' ')) + '; confidence: ' + esc(rule['confidence']) + '; rule: ' + esc(rule['source']) + '.</p><p>' + esc(rule['reason']) + '</p><p>' + esc(rule['screening_guidance']) + '</p><small>Review status: ' + esc(rule['review_status']) + '</small></li>')
        rows.append('<tr id="scat-' + esc(entry['scat_code']) + '" data-scat-row data-flags="' + esc(' '.join(flags)) + '"><th scope="row">' + esc(entry['scat_code']) + '</th><td>' + esc(entry['scat_description']) + '</td><td>' + esc(', '.join(sectors) or 'Primary-code dependent') + ('<p>Ambiguous / conditional evidence present</p>' if 'ambiguous' in flags else '') + '</td><td><details><summary>Why: ' + str(len(details)) + ' primary-code rules</summary><ul>' + ''.join(details) + '</ul></details></td></tr>')
    section = '''<section id="scat-classifications" aria-labelledby="scat-title">
<h2 id="scat-title">SCAT classifications and reasoning</h2>
<p>Category labels come from <a href="https://voaratinglists.blob.core.windows.net/html/documents/2026%20Draft%20Rating%20List%20and%20Draft%20Summary%20Valuation%20Data%20Specification.pdf#page=31">VOA specification Appendix 2</a>. The sector assignments and reasoning below are our interpretation of the recorded types, informed by the official RHL guidance linked above.</p>
<p>This is the complete list of SCAT codes in our reference/mapping tables and those observed in the VOA snapshot. These are <strong>our draft classifier interpretations</strong>, not official relief awards. Expand a code to see its primary-code rules, mapped sector, confidence, rationale and review status. Search includes the explanations inside each row.</p>
<p>A SCAT does not always have one classification. Text flags take priority, then primary+SCAT overrides, then SCAT-only overrides, then the primary-code fallback. Listed primary associations come from the mapping tables and observed records, not a restriction on other combinations. The * row explains other primary codes; the full primary-code download supplies their fallback rules.</p>
<p>“Other” means outside mapped RHL, not necessarily a statutory exclusion. Medium/low mapping confidence, generic shops and conditional activities require more evidence. Even high-confidence sector mappings still pass through property-level screening.</p>
<p><a href="/dataset/scat_classifications.csv" download>Download all SCAT rules and explanations (CSV)</a> · <a href="/dataset/scat_classifications.json" download>JSON</a> · <a href="/dataset/primary_classifications.csv" download>All primary-code fallback rules (CSV)</a></p>
<div class="scat-controls"><label>Search code, activity or explanation<input id="scat-search" type="search" placeholder="For example: 249, pharmacy, marina"></label><label>Classification evidence<select id="scat-filter"><option value="">All codes</option><option value="retail">Retail</option><option value="hospitality">Hospitality</option><option value="leisure">Leisure</option><option value="pub">Pub</option><option value="ambiguous">Ambiguous / conditional / primary-dependent</option><option value="outside">Outside mapped RHL / exclusion flags</option></select></label></div>
<p id="scat-count" role="status">''' + str(len(entries)) + ''' SCAT codes. Filters can overlap.</p>
<div class="table-wrap"><table><caption>Recorded categories and the classifier rules applied to them</caption><thead><tr><th>SCAT</th><th>Category</th><th>Mapped sector(s)</th><th>Classification reasoning</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table></div>
<h3>Text flags can override code mapping</h3><ul>'''
    for flag in payload['text_flags']:
        section += '<li><strong>' + esc(flag['sector'].replace('_',' ')) + '</strong>: ' + esc(flag['notes']) + ' Fields: ' + esc(flag['fields']) + '; confidence: ' + esc(flag['confidence']) + '; review: ' + esc(flag['review_status']) + '. Pattern: <code>' + esc(flag['pattern']) + '</code>.</li>'
    section += '</ul></section>'
    page = ROOT / 'web/methodology.html'
    content = page.read_text(encoding='utf-8')
    start, end = '<!-- SCAT AUDIT START -->', '<!-- SCAT AUDIT END -->'
    block = start + '\n' + section + '\n' + end
    if start in content:
        before, rest = content.split(start, 1); _, after = rest.split(end, 1); content = before + block + after
    else:
        anchor = '<section id="limits"'
        if anchor not in content:
            raise ValueError('Methodology insertion point not found')
        content = content.replace(anchor, block + '\n\n' + anchor, 1)
    assert content.count('data-scat-row ') == len(entries)
    page.write_text(content, encoding='utf-8')
    print(f'Generated {len(entries)} SCAT codes and {sum(len(e["rules"]) for e in entries)} effective primary-code rules.')


if __name__ == '__main__':
    main()
