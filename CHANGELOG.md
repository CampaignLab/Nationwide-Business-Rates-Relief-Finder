# Change history

This is the analytical and implementation history, not a record of confirmed business-rate awards. All figures below refer to the fixed source snapshot used on **3 November 2026**.

## Specific SCAT evidence and structured review categories — 3 November 2026

Specific SCAT activity evidence for convenience stores, takeaways and hair/beauty categories now resolves generic shop wording without overriding uncertain mapping confidence or contradictory evidence. Coded ancillary offices/stores no longer create conditional-use warnings by themselves for the limited recognised qualifying primary uses. Generic shops (249), uncertain pharmacies and conditional categories remain subject to checking.

Added review_categories, use_review_group and secondary_description_code to constituency exports. The browser displays the use assessment and separate concern flags. Rewrote the methodology from first principles; historical comparisons remain in this change history and the public comparison section.

The same input population now yields 26,446 likely candidates (up 1,815), 88,799 assigned review records and 181 unassigned review records. No assessments were added or removed from the 115,245 constituency-download population. Earley and Woodley has 18 likely and 73 review records. Validation: 153 Python tests, seven Node tests, and all 115,245 published rows across 543 constituencies checked for outcome/reason/category/count consistency. These checks do not establish relief entitlement.

## Documentation and sharing cleanup — 3 November 2026

Reworked the repository introduction and public methodology; added a source/checksum manifest, reproduction/release guide, field reference, current decision log and contribution/data-use notes. The documentation explains the different Earley comparison populations, distinguishes model outputs from awards, and supersedes outdated local-only and blanket marina-exclusion statements. This cleanup does not change source data, screening rules or published counts.

## Conservative national screening — 3 November 2026

Implemented in [e654a08](https://github.com/CampaignLab/Nationwide-Business-Rates-Relief-Finder/commit/e654a086bbdb35bd025d7a6d61052b83c5010fce).

- Added a separate screening layer: likely candidate, needs review and outside target. Retained the earlier model fields for comparison.
- Routed generic shops, conditional uses, possible exclusions, terminated/unmatched postcodes and multiple-name matches to review. Name matching no longer proves exclusion in the public screening list.
- Reconsidered recreational marinas against current guidance. Unspecified marina use requires review.
- Retained missing/malformed postcodes for unassigned review; deleted-property proxy records without a rateable value remain rejected.
- Added 61 non-empty spreadsheet-supplied trading-name records with source and unverified status, without using them as automatic eligibility evidence.
- Added sourced property-use warnings, billing-authority homepage links, RV filters, separate list views, filtered downloads and a public methodology.

### National results

| Measure | Assessments |
|---|---:|
| Previous publication, assigned to English constituencies | 108,684 |
| Revised likely candidates | 24,631 |
| Revised needs review, assigned to constituencies | 90,614 |
| Revised needs review, unassigned | 181 |
| Revised constituency downloads, both lists combined | 115,245 |
| All English assessments within the target RV band | 240,163 |
| Target-band assessments classified outside target by recorded use | 124,737 |

The earlier and revised published totals have different screening definitions. The review list now retains some conditional cases and name-matched records omitted by the earlier model. A smaller likely list does not establish that all other assessments are ineligible. See the [machine-readable report](web/dataset/screening_report.json) for reconciliations; its legacy-model transition table uses the **updated** mapping, not a frozen copy of every old published row.

### Earley and Woodley comparison

The independent spreadsheet has 64 assessments; the old live list has 88. They share 56, leaving eight spreadsheet-only and 32 old-list-only assessments: **96 distinct references**.

| Comparison population | Likely | Review | Outside target |
|---|---:|---:|---:|
| All 96 comparison references, including other/unresolved locations | 16 | 76 | 4 |
| The previous 88-record Earley live list | 16 | 72 | 0 |
| The independent 64-record spreadsheet | 8 | 52 | 4 |

The revised constituency file itself has **16 likely and 75 review records**. It is not the same population as the 96-record benchmark: the benchmark includes Reading Central and unresolved-location records; the revised constituency file also retains a store assessment absent from both earlier lists.

The eight spreadsheet-only records comprise three at exactly £12,000, two assigned by ONS to Reading Central, two store assessments and one golf-club site-office assessment with a postcode discrepancy. The latter is outside target on recorded use. The spreadsheet's golf-club identity does not establish that a separately assessed office is qualifying leisure premises.

Checks: **147 Python tests**, **7 Node tests**, verification of **115,245 published constituency rows**, and browser checks of the default view, review reasons, RV filters and an actual 16-row filtered Earley download. These test software behaviour and data consistency; they do not measure real-world eligibility accuracy.

## Comparison with the alternative implementation — 3 November 2026

We ran [CampaignLab/business-rates-relief](https://github.com/CampaignLab/business-rates-relief/tree/a375373ae33869b1092d2233c81272b8b680c963) against the same VOA and ONS snapshots.

It models broader 2026/27 relief in England and Wales, including RHL multipliers. Its April 2027 view was documented as proposed, not implemented at that commit. Its broad Earley set contains 1,344 potentially eligible assessments, or 1,091 with its likely-trading filter. Restricting it to English RHL assessments above £12,000 and up to £18,000 reproduces the same 88 references as our previous Earley publication.

That agreement is reproducibility evidence, not independent validation of qualifying use. The comparison exposed shared generic-shop/estate-agency issues, supported revisiting our marina mapping, and illustrated the risk of approximate postcode-sector assignment. We retained exact matching and adopted conservative review separation in the original repository.

## Initial public finder — 3 November 2026

Published in [67fa6f9](https://github.com/CampaignLab/Nationwide-Business-Rates-Relief-Finder/commit/67fa6f9f3d69baf796657e2ee929941cedbe785d), following development of the web browser around the original Python/DuckDB pipeline.

The first public target cohort contained **108,842 assessments nationally**, of which **108,684** had an English constituency and **158** did not. Publication used a single legacy model flag. It did not have the later likely/review distinction. These figures are archived in `config/previous_publication.json`.
