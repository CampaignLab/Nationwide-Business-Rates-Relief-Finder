# Data dictionary

Schema for the conservative screening publication introduced on **3 November 2026**. A row is a **VOA property assessment**, not a verified business or legal ratepayer account.

## Files and formats

| File | Contents |
|---|---|
| `constituencies/csv/*.csv` | Assigned likely and review records; provider/methodology notice lines precede a blank line and the column header |
| `constituencies/xlsx/*.xlsx` | Same records, with separate **Notice** and **Properties** sheets |
| `constituency_index.json` | Snapshot/rule metadata, constituency counts and file paths; `screening_version` is 1 |
| `screening_report.json` | National screening counts, previous-publication totals, legacy-model comparison and benchmark counts |
| `earley_comparison.csv` | Plain-header CSV of all 96 comparison references, including other/unresolved locations and outside-target outcomes |
| `unassigned_review.csv` | Plain-header CSV of review assessments without an English constituency; wider intermediate-source schema, using `uarn` for the property reference |

Public copies live in `web/dataset/` in the repository and `/dataset/` on the website. Rebuilt copies are first written to `out/`. Internal intermediates and `out/run_report.md` are not automatically staged.

Constituency CSV files have a UTF-8 BOM and introductory notices. Do not read them as if the first line is the header. For example:

```python
import csv

with open("constituency.csv", encoding="utf-8-sig", newline="") as stream:
    reader = csv.reader(stream)
    header = next(row for row in reader
                  if "property_reference" in row and "screening_outcome" in row)
    records = [dict(zip(header, row)) for row in reader if row]

likely = [row for row in records if row["screening_outcome"] == "likely_candidate"]
```

The browser's filtered CSV contains every matching row, even when the table displays only the first 100. It includes the screening disclaimer but not the full introductory provider notices from the original constituency file; retain the original notices and source links with redistributed extracts. Formula-like text is escaped in this browser export, so it is a display-oriented extract rather than a byte-identical copy of source fields.

## Identity, assessment and geography

| Field | Meaning |
|---|---|
| `property_reference` | VOA Unique Address Reference Number (`uarn`, source item 7). Keep as text; it is not a company number or the council's account reference. |
| `address` | Original full property identifier supplied by VOA. |
| `postcode` | Normalised postcode used for exact geography matching. Original postcode text is retained in intermediate data. |
| `firm_name` | Original VOA firm-name text, often missing or generic; not a verified occupier. |
| `constituency_code`, `constituency_name` | ONS 2024 Westminster constituency identifiers from an exact postcode match. |
| `billing_authority_code`, `billing_authority` | VOA billing-authority code and name, independent of constituency. Preserve leading zeroes in the code. |
| `is_london` | Whether the VOA billing authority is in the London grouping used by the legacy model. |
| `rateable_value` | VOA assessment value in pounds. This is not the annual rates bill. |
| `description_text`, `description_code`, `scat_code` | Original recorded premises description/codes; SCAT adds detail to broad description codes. |
| `sector`, `sector_confidence` | Mapping-derived sector and qualitative confidence in that mapping, not council-confirmed actual use or probability of an award. |
| `snapshot_epoch` | VOA epoch identifier; 0004 in this release. |

The original billing authority's own property reference (`ba_reference`) and assessment/case references are available in intermediate data, but are not columns in the current constituency export. A council may need address/postcode information to cross-reference its account.

## Screening fields — use these for the public lists

| Field | Meaning |
|---|---|
| `screening_outcome` | `likely_candidate`, `needs_review` or `outside_target`. Constituency downloads contain the first two; the comparison file also contains outside-target outcomes. |
| `screening_reason` | Plain-English explanation of that outcome. |
| `review_reasons` | Review explanation when the outcome is `needs_review`; otherwise empty. |
| `evidence_source` | Source for a separately maintained property-use warning, where present. |
| `verified_with_council` | Blank worksheet field reserved for a user's checks; this release does not populate it or claim verification. |

`outside_target` means outside this particular screen, not proof of ineligibility for all relief. Missing names alone do not cause review. The [methodology](METHODOLOGY.md) sets out the actual selection logic.

## Supplied trading names and council URLs

| Field | Meaning |
|---|---|
| `trading_name` | Optional separately supplied name displayed ahead of the VOA name/address. |
| `name_source` | Workbook/sheet/row or another recorded source for the supplied name. |
| `name_recorded_date` | Date recorded/imported into this project, not necessarily the source's research date. |
| `name_verification_status` | Currently `unverified_spreadsheet_supplied` for workbook names. |
| `council_url` | Directory-sourced official council homepage, sometimes a successor authority. |
| `council_link_source` | Government directory URL from which the homepage was obtained. |
| `council_link_checked_date` | Directory retrieval/source-check date. It does not mean the council confirmed a record or every homepage was individually availability-tested. |

## Legacy model fields — retained for comparison

| Field | Meaning |
|---|---|
| `firm_property_count` | Number of English assessments with the same normalised VOA firm name. Equal names do not establish the same legal occupier. |
| `status_now` | Modelled pre-April-2027 SBRR result under configuration assumptions. |
| `status_from_apr_2027` | Earlier model's announced-rule result; labels such as `eligible_from_apr_2027` do not confirm entitlement. |
| `relief_now`, `relief_from_apr_2027` | Modelled fraction of relief, between 0 and 1. A value of 1 is not evidence that the council awarded 100% relief. |
| `target_new_full_relief` | Per-property Boolean from the earlier model; does not drive the new candidate/review split. |
| `reason` | Explanation of the earlier model's two time views. Use `screening_reason` for the current list decision. |

The legacy model's aggregate-property-limit interpretation remains an assumption. The conservative screen flags multiple-name matches for review rather than using them as proof of entitlement or exclusion.

### Important index compatibility detail

In `constituency_index.json`, `counts.likely_candidate` and `counts.needs_review` are the new list counts. Their sum equals `counts.target_new_full_relief`. That **index count** retains its historical name but now counts all exported screening records; it is not a count of rows whose per-property legacy flag is true. `counts.properties_in_list` counts all English assessments in that constituency, not just the exported cohort. Older `now_*`/`apr2027_*` breakdowns describe model outputs within the exported cohort.

Use the new outcome counts and `screening_version: 1` when integrating. Do not treat every numerical or Boolean eligibility field as interchangeable.
