# How the finder works

Methodology for the **3 November 2026** publication. [Open the public explanation](https://business-rates-relief-finder-campaign-lab.vercel.app/methodology.html) · [Change history](../CHANGELOG.md) · [Field reference](DATA_DICTIONARY.md)

## The question we are screening for

Which English property assessments have a rateable value **above £12,000 and up to £18,000 inclusive**, and recorded premises use consistent with the announced expansion of full small business rates relief (SBRR) for retail, hospitality and leisure (RHL) from **1 April 2027**?

The underlying policy purpose is to identify businesses that could newly have nothing to pay. The available property data cannot establish that outcome. We publish an automatic candidate screen with a conservative main list and a separate review list. “Likely” is not a statistically calibrated confidence score.

## Inputs and provenance

| Input | Version used | Role |
|---|---|---|
| [VOA rating-list downloads](https://voaratinglists.blob.core.windows.net/html/rlidata.htm) | 2026 current list entries, compiled epoch 0004 baseline; file dated 1 October 2026, latest record date 29 September 2026 | Original assessment reference, address, description, firm name and rateable value |
| [ONS Open Geography Portal](https://geoportal.statistics.gov.uk/) | ONSPD August 2026, using 2024 parliamentary constituencies | Exact postcode-to-constituency match and names |
| [Budget technical annex](https://www.gov.uk/government/publications/82026-details-of-the-budget-package-and-the-multipliers-for-20272028/82026-details-of-the-budget-package-and-the-multipliers-for-20272028) | Announcement dated 28 October 2026; page updated 30 October | Threshold and policy assumptions for April 2027 |
| [Official RHL guidance](https://www.gov.uk/guidance/business-rates-multipliers-qualifying-retail-hospitality-or-leisure) | Guidance updated 30 March 2026 | Basis for interpreting premises types, alongside mapping judgements |
| [Government council directory](https://www.planning.data.gov.uk/dataset/local-authority) | Retrieved 3 November 2026 | Official council homepage links |
| Independent Earley and Woodley workbook | Supplied for comparison; name records recorded 3 November 2026 | 64 assessment references and 61 non-empty supplied trading-name entries |

The policy configuration is a dated announcement model, marked **announced, not yet in regulations** in this release. The RHL guidance supports a premises-use screen; it does not replace the final April 2027 rules or a council's decision. The deployed site does not fetch new source data or rule changes automatically.

The [source manifest](SOURCES.json) provides the exact input ZIP sizes and SHA-256 checksums, plus the analysis commit used for these results.

## Processing steps

### 1. Read and validate the assessment data

The parser follows the VOA's asterisk-delimited, headerless specification. Rateable value is **item 18**, counted from one. A workbook with an added name column has different physical column positions, so visual spreadsheet column numbers are not used as the parser schema.

The pipeline checks the trailing empty field, row counts and unique assessment references. Blank RV records are VOA deleted-property proxies and are set aside with reasons. Missing or malformed postcodes are retained; their original text remains in the intermediate data.

The fixed baseline has 2,178,394 rows; 34,858 deleted-property proxies are rejected, leaving 2,143,536 assessments. Billing-authority codes select 2,017,567 English assessments and exclude 125,969 Welsh assessments. Records at £0 remain in the pipeline but fall outside the target band.

### 2. Select the value band

| Rateable value | Target selection |
|---|---|
| £12,000 or less | Outside this expansion target; may already be within the old full-relief band |
| Above £12,000 to £18,000 inclusive | Target band, subject to premises-use and uncertainty screening |
| Above £18,000 | Outside this full-relief target; some may fall within a separate taper band |

Rateable value is an assessment value, **not the annual bill or relief amount**. Properties below £15,000 may already have some tapered SBRR. Other existing reliefs can already reduce a bill to zero. The band alone therefore cannot identify a newly zero bill.

### 3. Classify recorded premises use

The initial sector mapping uses, in descending precedence:

1. Description/name text flags for activities such as possible vape shops, adult gaming centres or dance schools.
2. Primary-description-code and SCAT-code overrides.
3. Wildcard SCAT overrides.
4. The primary description code; otherwise an uncertain/unmapped classification.

The conservative screen then reads the original VOA description/name information and the mapping confidence. It considers generic retail wording, mixed or conditional use, possible excluded activity and separately recorded property-specific evidence. A generic shop description does not establish whether the premises is a qualifying retailer or an excluded professional service.

Recreational marinas can qualify under the guidance. Unspecified marinas and moorings require review. A business name suggesting leisure does not establish the use of a separately assessed office or store. Explicitly excluded descriptions are outside target; less definite concerns are retained for review. These rules are heuristics and cannot identify all excluded uses.

All sector-map rows currently await formal human sign-off. Mapping confidence reflects an interpretation of recorded type; it is not measured eligibility accuracy. See the actual rules in [screening.py](../src/screening.py) and the version-controlled [mapping tables](../mapping/).

### 4. Match geography and council information

We use an exact postcode join to ONSPD. There is no postcode-sector approximation. A terminated-postcode match retains its geography but needs review. Unmatched postcodes and assessments without an English constituency remain unassigned. Only unassigned assessments otherwise retained as review candidates enter the national unassigned-review download.

The billing council is taken from the **VOA billing-authority code**, not inferred from constituency. URLs were joined to the government's council directory using address-custodian identifiers. Named exceptions were used for Buckinghamshire (0440), Dorset (1265), Malvern Hills (1860), Isle of Wight (2100), Somerset West and Taunton to Somerset (3330), East Suffolk (3540), and West Suffolk (3545).

These are directory-sourced official homepages, sometimes a successor council's site. Their retrieval/source date is recorded. Not every endpoint has been individually checked for current availability, and the links do not confirm relief. Find the council's business-rates section for an individual check.

### 5. Keep identity and ratepayer uncertainty visible

The VOA firm-name field is often blank or generic. Original firm names are retained. Names are normalised and grouped across England to flag possible multiple occupation; equal names are not proof of a common legal ratepayer. A group moves a candidate to review. Missing names neither prove sole-property occupation nor cause review by themselves.

The independent workbook supplies 61 non-empty trading-name entries. These are matched by property reference and displayed as **unverified spreadsheet-supplied names**, with workbook/sheet/row and recording date. They may identify a site, owner or operator rather than the ratepayer. They do not independently establish eligibility. Sourced use concerns are maintained separately in `mapping/property_review_evidence.csv`.

## The three outcomes

| Outcome | Meaning | Publication |
|---|---|---|
| Likely candidate | In band; mapped qualifying use with no detected screening conflict | Default constituency view |
| Needs review | Potentially relevant, but one or more recorded concerns prevent the clearer classification | Separate constituency view, or unassigned review file |
| Outside target | Outside the RV band or recorded use is not retained as qualifying/conditional | Retained in intermediate results; included in the 96-reference comparison where applicable |

“Outside target” does not establish that no business rates relief of any kind is available. A review outcome does not prove ineligibility. Publication in the main list does not prove occupation, entitlement or a zero bill.

## Results and comparison

The fixed release contains **24,631 likely candidates**, **90,614 assigned review assessments** and **181 unassigned review assessments**, across **543 English constituencies**. The 115,245 constituency download rows reconcile to the first two groups. A further 124,737 English target-band assessments are outside target by recorded use. Totals are assessments, not unique businesses.

The independent spreadsheet's 64 records and previous live list's 88 records share 56 references, giving a **96-reference benchmark**. All shared comparisons use the same VOA snapshot; recorded RVs agree. Of the eight spreadsheet-only records, three are exactly £12,000, two are in Reading Central, two are stores requiring use checks, and one is a golf-club site-office assessment with a postcode discrepancy.

The benchmark now has **16 likely, 76 review and four outside-target records**. The current Earley constituency file has **16 likely and 75 review records**: it is a different population, excluding other/unresolved locations and adding a store record absent from both earlier lists. The old 88 records split into 16 likely and 72 review records. Neither list is treated as ground truth.

We also ran the [alternative repository at a fixed commit](https://github.com/CampaignLab/business-rates-relief/tree/a375373ae33869b1092d2233c81272b8b680c963). Its broader model concerns 2026/27 relief. Applying comparable RV/RHL filters reproduced our previous 88 Earley references, including shared classification concerns. Its review of marinas helped identify a gap in our original mapping; its approximate geography approach was not adopted.

See [CHANGELOG.md](../CHANGELOG.md) for the detailed before/after tables, [all 96 comparison outcomes](../web/dataset/earley_comparison.csv), and the [national report](../web/dataset/screening_report.json).

## Validation and remaining uncertainty

The screening release passed 147 Python tests and seven Node tests. Checks cover threshold boundaries, review/exclusion behaviour, name-match uncertainty, missing postcodes, row conservation, unique references, output-count reconciliation and website/export agreement. Browser checks included the default/review views, RV filtering and an actual filtered download.

These are software and consistency checks. We have **not** conducted a representative council-verified audit, measured precision/recall, confirmed all current uses or ratepayers, or established actual relief receipt. Source changes, stale names, unusual uses, ratepayer circumstances and final regulations can change the answer. All mappings remain draft.

The earlier status/percentage fields are retained as model outputs for compatibility, not current awards. In particular, the legacy aggregate-property-limit interpretation remains an assumption. Use `screening_outcome` and `screening_reason` for this publication; see the [field reference](DATA_DICTIONARY.md).

## Before making a definitive statement

Confirm the current occupier and liable ratepayer, current qualifying use, other occupied properties, applicable rules and effective date, existing reliefs and actual council award/bill. To establish a **newly** zero bill, also establish the previous amount payable and why the bill changes.

For an unverified case, a suitable invitation is: **“This property may qualify for expanded relief. Please check your circumstances with your council.”**

> These properties appear likely to qualify for expanded full small business rates relief based on their rateable value and recorded premises use. The data does not confirm the current occupier, their other properties, existing reliefs or final bill. Before telling a business that it will have nothing to pay, confirm its circumstances with the linked billing council.

Read [Data use and attribution](DATA_USE.md) before reusing the records. Report evidence-backed corrections through [CONTRIBUTING.md](../CONTRIBUTING.md).
