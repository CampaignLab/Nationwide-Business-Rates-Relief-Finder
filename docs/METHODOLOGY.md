# How the property classifier works

## Purpose

We identify English property assessments whose rateable value and recorded use are consistent with potential eligibility for the announced expansion of full Small Business Rate Relief for retail, hospitality and leisure (RHL) from **1 April 2027**.

One record is a **VOA property assessment**, not a verified business or legal ratepayer. We screen evidence about premises; we do not determine awards. “Likely” is a rule-based category, not a measured probability or confidence interval.

## Sources

- VOA 2026 compiled rating list, epoch 0004: file dated 1 October 2026, latest record date 29 September. Supplies assessment identifiers, descriptions, codes, addresses, supplied firm names and rateable values.
- ONS postcode directory, August 2026: exact postcode geography using 2024 parliamentary constituencies.
- Budget technical annex, announced 28 October 2026 and updated 30 October: April 2027 policy assumptions.
- Official RHL guidance: informs premises-use interpretation, not final April 2027 entitlement.
- Official council directory: links to billing councils.
- Separately sourced names and property evidence: retained with provenance; unverified trading names do not prove qualifying activity.

Exact source hashes are in [SOURCES.json](SOURCES.json). The policy configuration models an announcement, marked **not yet in regulations**. All sector mappings await formal human sign-off. Sources and rules do not update automatically.

## 1. Parse the assessment evidence

Read the VOA's headerless, asterisk-delimited format. Rateable value is item 18. Check the trailing empty field, row counts and reference uniqueness. Set aside blank-value records as deleted-property proxies. Retain missing/malformed postcodes rather than silently repairing them. Billing-authority codes select English assessments.

The key evidence is primary/secondary description code, actual description text, SCAT category, rateable value, address, postcode and billing-authority code. Original firm names are sparse and do not reliably identify the legal ratepayer. Individually entered (“overtyped”) descriptions can be more specific than standard code descriptions.

## 2. Select the value band

Keep rateable values **greater than £12,000 and no greater than £18,000**. Exactly £12,000 falls in the previous full-relief band. Above £18,000 is outside this full-relief search even if a taper or another relief applies.

Rateable value is an assessed rental value, not the annual bill. Some properties already receive tapered SBRR or other reliefs. The band alone cannot identify a newly zero bill.

## 3. Map recorded premises use

Apply the following rules in descending precedence:

1. Specific text flags in `mapping/text_flags.csv` for possible vape shops, gaming centres and dance schools, using each rule's specified source fields.
2. Primary-description-code plus SCAT overrides in `mapping/scat_overrides.csv`.
3. Wildcard SCAT overrides applying across primary codes.
4. Primary-code mapping in `mapping/sector_map.csv`.
5. Unmapped records become other, with low mapping confidence.

The SCAT category uses the first three characters. Recognised secondary suffixes are separated from the primary code. The result records sector, mapping source and high/medium/low confidence. These labels reflect an interpretation of recorded premises type, not calibrated eligibility probabilities. Code and text can conflict or be out of date.

## 4. Assess activity evidence

Qualifying mapped sectors are retail, hospitality, leisure and pub. Specific descriptions such as hairdressing salon give stronger evidence than a generic shop.

SCAT **106** (convenience stores), **442** (takeaways), **417** and **507** (hair/beauty classifications) provide specific activity evidence where the mapped sector is RHL. They suppress the generic-shop warning, but do not upgrade uncertain mapping confidence or override conflicts.

Generic shops, including SCAT **249**, require actual-use checks unless a recognised specific description resolves the ambiguity. Estate agents can share this category with qualifying retailers. Pharmacies and other uncertain categories are not automatically promoted merely because their SCAT is specific.

Explicit excluded-use wording in the premises description produces outside_target. Less definite signals in original names/address text produce review warnings. These phrase rules are heuristics and do not detect every excluded activity.

Non-RHL sectors are outside target unless retained as potential conditional uses, such as stores, marinas or stables. Explicit recreational marina wording is treated separately; unspecified marinas/moorings need review.

## 5. Interpret secondary codes

Secondary suffixes are **W** workshop, **S** store, **C** car space and **O** office. These differ from the separate composite indicator C for mixed domestic/business property. No suffix does not prove the absence of supporting accommodation.

For primary codes CS, CS3, CS5, CS6, CS8, CS9, CR and CR1, an explicitly coded ancillary office/store does not itself trigger conditional-use review when specific description/SCAT evidence exists, or the primary code identifies a cafe/restaurant. This is a narrow exception. Workshop, explicit mixed use and other conditional wording still require checks. Post office is recognised as an activity, rather than an ancillary-office warning.

A retail trading name does not make a separately assessed office or store qualifying retail premises.

## 6. Keep geography and ratepayer concerns separate

Postcodes join exactly to ONSPD. There is no postcode-sector approximation. Terminated-postcode matches retain geography with a warning. Missing English constituency matches remain unassigned. Billing councils come from VOA authority codes, not constituencies. Official directory links may point to successor councils; they do not prove an award or guarantee current endpoint availability.

Normalised firm names appearing on multiple assessments trigger a warning. Matching names do not prove common legal liability. Brands and franchises are not automatically excluded. Missing names do not establish single-property occupation.

Supplied trading names are displayed separately with source, date and unverified status. Property-specific concerns are stored in `mapping/property_review_evidence.csv`.

## 7. Assign outcomes and review categories

| Outcome | Decision |
|---|---|
| likely_candidate | In band, sufficiently strong qualifying-use mapping, no detected screening warnings. Entitlement remains unconfirmed. |
| needs_review | Potentially relevant, with activity, evidence, location or ratepayer concerns. |
| outside_target | Outside the value band, explicitly excluded use, or use not retained by the qualifying/conditional screen. Other relief may still apply. |

| Review category | Meaning |
|---|---|
| possible_exclusion | Name/address or activity flag suggests possible excluded use. |
| conditional_use | Qualifying activity is not established for conditional/mixed premises. |
| generic_shop | Generic retail evidence does not establish actual activity. |
| uncertain_sector | Sector mapping is below high confidence. |
| location | No exact English constituency match, or terminated postcode. |
| ratepayer | Repeated firm name suggests multiple occupation without proving it. |
| property_evidence | Separately sourced property-specific concern. |

`review_categories` contains all applicable flags, separated by semicolons; counts overlap. `use_review_group` selects the first applicable use/evidence category in the order above, ignoring location/ratepayer. It is clear_recorded_use where only those latter concerns remain, or outside_target for excluded records. This is a presentation priority, not an independent eligibility determination. `secondary_description_code` exports the suffix or a blank value.

Location/ratepayer warnings retain the overall needs_review outcome even where recorded use is clear.

## 8. Publish and validate

Assigned likely/review records are published by constituency in CSV and Excel. Entries and downloads show the primary code and standard label, secondary accommodation suffix and label, and SCAT category and label alongside the original combined codes and actual description. These labels explain the recorded classifications and do not change the screening decision. Unassigned review records have a national download. Counts represent assessments, not unique businesses.

Checks cover threshold boundaries, specific SCAT evidence, conflicts, ancillary-space handling, review categories, geography, row conservation, reference uniqueness, output counts and website/export consistency. They verify software behaviour, not actual eligibility accuracy. Code, mappings and published outputs are versioned; source ZIPs and intermediates are not committed.

## Before promising relief

Verify the current occupier, liable ratepayer, actual qualifying use, other occupied properties, final applicable rules, effective date, existing reliefs and council decision. To claim a newly zero bill, establish the previous amount payable and why it changes.

There has been no representative council-verified audit establishing precision, recall or statistical confidence intervals. A suitable invitation is: **“This property may qualify for expanded relief. Please check your circumstances with your council.”**

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for fields, [DATA_USE.md](DATA_USE.md) for reuse and attribution, and [CHANGELOG.md](../CHANGELOG.md) for version history.

## Current snapshot counts

The 3 November 2026 output has **26,446 likely candidates**, **88,799 assigned review assessments** and **181 unassigned review assessments**. Constituency downloads contain 115,245 assessments across 543 constituencies. Another 124,737 target-band assessments are outside target by recorded use.
