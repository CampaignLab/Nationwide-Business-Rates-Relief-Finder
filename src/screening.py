"""Conservative property screening, separate from modelled relief/entitlement."""
import re

DISCLAIMER = ('These properties appear likely to qualify for expanded full small business rates relief based on their '
              'rateable value and recorded premises use. The data does not confirm the current occupier, their other '
              'properties, existing reliefs or final bill. Before telling a business that it will have nothing to pay, '
              'confirm its circumstances with the linked billing council.')
RHL = {'retail', 'hospitality', 'leisure', 'pub'}
EXCLUDED = re.compile(r'\b(estate agen\w*|letting agen\w*|financial services|bank|insurance|veterinary|betting office)\b', re.I)
CONDITIONAL = re.compile(r'\b(store|storage|warehouse|office|workshop|mixed|land|moorings?|marina|stables?|kennels?|catter\w*)\b', re.I)
SPECIFIC_RETAIL = re.compile(r'\b(hairdress\w*|barber\w*|salon|beauty|nail|florist|baker\w*|butcher|grocer|newsagent|chemist|pharmacy|optician|post office|launder\w*|dry clean\w*|shoe repair|key cut\w*|garden cent\w*|petrol|supermarket|convenience|off licen\w*|car showroom)\b', re.I)


# Deliberately narrow: these identify activity, unlike generic shops (249).
# This supplements, rather than upgrades, the existing sector confidence.
SPECIFIC_SCAT = {'106', '442', '417', '507'}


def secondary_code(p):
    code = p.get('description_code') or ''
    primary = p.get('primary_description_code') or ''
    return code[-1:] if primary and code[:-1] == primary and code[-1:] in {'W', 'S', 'C', 'O'} else ''


def screen(p):
    rv = p['rateable_value']
    if not 12000 < rv <= 18000:
        return 'outside_target', 'Outside the target band: rateable value must be above £12,000 and up to £18,000.'
    # Only original VOA text is used for automatic classification, never an unverified researched name.
    text = ' '.join(str(p.get(k) or '') for k in ('description_text', 'firm_name', 'number_or_name'))
    sector = p.get('sector', 'other')
    description=p.get('description_text') or ''
    if EXCLUDED.search(description):
        return 'outside_target', 'VOA text indicates an excluded use. Actual use and any change must be checked.'
    scat = str(p.get('scat_code') or '')[:3]
    specific_scat = scat in SPECIFIC_SCAT and sector in RHL
    conditional_text = re.sub(r'\bpost office\b', '', description, flags=re.I)
    # A coded ancillary office/store does not by itself establish uncertain use.
    # Do not remove workshop warnings or explicit mixed-use wording.
    suffix = secondary_code(p)
    primary = p.get('primary_description_code') or ''
    if primary in {'CS', 'CS3', 'CS5', 'CS6', 'CS8', 'CS9', 'CR', 'CR1'} and (specific_scat or SPECIFIC_RETAIL.search(description) or primary in {'CR', 'CR1'}):
        ancillary = {'O': r'\boffices?\b', 'S': r'\bstores?\b'}.get(suffix)
        if ancillary:
            conditional_text = re.sub(ancillary, '', conditional_text, flags=re.I)
    conditional = bool(CONDITIONAL.search(conditional_text))
    recreational_marina = bool(re.search(r'\b(recreational|pleasure|leisure)\b', description, re.I)) and bool(re.search(r'marina|mooring|jetty|pier', description, re.I))
    conditional_candidate=bool(re.search(r'\b(marina|moorings?|jetty|pier|store|stables?|kennels?|catter\w*)\b',description,re.I))
    if sector not in RHL and sector not in {'possible_vape_shop', 'possible_adult_gaming_centre'} and not conditional_candidate and not recreational_marina:
        return 'outside_target', 'Recorded premises use is not mapped to qualifying retail, hospitality or leisure.'
    reasons = []
    if EXCLUDED.search(text):
        reasons.append('Name or address text suggests an excluded use; current actual use needs checking')
    if not p.get('constituency_code'):
        reasons.append('No exact English constituency match; location needs checking')
    elif p.get('postcode_terminated'):
        reasons.append('Matched postcode is terminated; current location needs checking')
    if (p.get('firm_property_count') or 0) > 1:
        reasons.append('Firm name also appears on other assessments; this does not prove a common ratepayer')
    if sector in {'possible_vape_shop', 'possible_adult_gaming_centre'}:
        reasons.append('Possible excluded activity; definition and actual use require checking')
    if conditional and not recreational_marina:
        reasons.append('Conditional or mixed premises use; public-facing qualifying activity is not established')
    generic_shop=bool(re.match(r'^SHOP(?:\s|$)',description,re.I)) and not SPECIFIC_RETAIL.search(description)
    if not specific_scat and (generic_shop or (sector == 'retail' and not SPECIFIC_RETAIL.search(description))):
        reasons.append('Generic retail description does not establish actual qualifying use')
    if p.get('sector_confidence') != 'high' and not recreational_marina:
        reasons.append('Sector mapping is uncertain')
    if p.get('evidence_warning'):
        reasons.append(p['evidence_warning'])
    if reasons:
        return 'needs_review', '; '.join(reasons) + '.'
    return 'likely_candidate', 'Within the target value band; recorded premises use indicates qualifying RHL with no detected screening conflict. Occupation, ratepayer circumstances and actual entitlement remain unconfirmed.'


def screen_details(p):
    """Stable review categories, separate from the backward-compatible outcome."""
    outcome, reason = screen(p)
    checks = (
        ('possible_exclusion', ('suggests an excluded use', 'Possible excluded activity')),
        ('conditional_use', ('Conditional or mixed premises use',)),
        ('generic_shop', ('Generic retail description',)),
        ('uncertain_sector', ('Sector mapping is uncertain',)),
        ('location', ('No exact English constituency', 'postcode is terminated')),
        ('ratepayer', ('Firm name also appears',)),
    )
    categories = [key for key, phrases in checks if any(s in reason for s in phrases)] if outcome == 'needs_review' else []
    if outcome == 'needs_review' and p.get('evidence_warning'):
        categories.append('property_evidence')
    use_categories = [c for c in categories if c not in {'location', 'ratepayer'}]
    use_group = use_categories[0] if use_categories else ('clear_recorded_use' if outcome != 'outside_target' else 'outside_target')
    return dict(screening_outcome=outcome, screening_reason=reason,
                review_categories=';'.join(categories), use_review_group=use_group,
                secondary_description_code=secondary_code(p))
