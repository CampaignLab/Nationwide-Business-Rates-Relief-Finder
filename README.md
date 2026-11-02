# Business Rates Relief Finder

Version one. This tool reads the Valuation Office (VO, formerly VOA) 2026 non-domestic rating list for England. It flags properties that may be eligible for Small Business Rate Relief (SBRR), now and under the rules announced for 1 April 2027. It assigns each property to a 2024 parliamentary constituency and writes one file per constituency.

## Licence warning: read before using the outputs

The VO publishes the rating list under a **restricted licence**, not the Open Government Licence ([terms](https://www.tax.service.gov.uk/view-my-valuation/terms-and-conditions)). The terms limit use to non-domestic rating purposes, such as viewing assessments and reviewing valuations by occupiers, owners, councils and their representatives. They prohibit onward disclosure to anyone whose use is outside those purposes. The terms also do not cover personal data.

Giving constituency files to MPs' offices and campaigners so they can contact businesses may fall outside these terms. **Do not distribute any output until the VO has confirmed in writing that the use is permitted** (ccaservicevo@hmrc.gov.uk) **and you have taken data protection advice.** Every output file carries this warning.

## What it shows and what it does not

It shows properties whose rateable value and property type suggest they **may** qualify for relief. Each row has a status and a plain-English reason.

It does not show:

- who pays business rates on a property
- who receives relief now
- whether a property is occupied
- whether the occupier has other properties. The firm name field is filled in on only 3.5% of entries, so for most small businesses this cannot be checked.

No status means a business is eligible or receives relief. Check eligibility with the billing authority before contacting a business.

## Personal data

Some firm names are sole traders, and some premises are home addresses: for example, self-catering holiday units and composite properties with living accommodation. The constituency files are for authorised users only. Do not build any public-facing output from them. Take data protection advice before any wider distribution or outreach.

## Input files

Neither file is included in this repository. Place both, still zipped, in `data/raw/`.

1. **VO rating list.** Go to the [VO rating list downloads page](https://voaratinglists.blob.core.windows.net/html/rlidata.htm), accept the terms, and download the 2026 list entries baseline, for example `uk-englandwales-ndr-2026-listentries-compiled-epoch-0004-baseline-csv.zip`. If there are several, stage 1 uses the highest epoch.
2. **ONS Postcode Directory (ONSPD).** Download the latest release (for example `ONSPD_AUG_2026.zip`) from the ONS Open Geography Portal. The pipeline reads `Data/ONSPD_MMM_YYYY_UK.csv` and the constituency and region names files in `Documents/`. ONSPD field names change between releases. If stage 3 stops with a missing-field error, check Annex A of the release's user guide and update `ONSPD_FIELDS` in `src/03_constituency.py`.

## Running

Python 3.11 or later.

```
make setup     # create .venv and install pinned requirements
make           # run tests, then stages 1 to 7; stops at the first failure
make test      # tests only
```

Without make: `python run_all.py`. Each stage can also be run on its own, for example `python src/04_sector.py`. Each stage reads the previous stage's output and overwrites its own.

| Stage          | Script                   | Output in `data/work/`                       |
| -------------- | ------------------------ | -------------------------------------------- |
| 1 Ingest       | `src/01_ingest.py`       | `rating_list.parquet`, `metadata.parquet`    |
| 2 Clean        | `src/02_clean.py`        | `clean.parquet`, `rejected_rows.csv`         |
| 3 Constituency | `src/03_constituency.py` | `england.parquet`, `unmatched_postcodes.csv` |
| 4 Sector       | `src/04_sector.py`       | `sectored.parquet`, `sector_coverage.csv`    |
| 5 Occupiers    | `src/05_occupiers.py`    | `occupiers.parquet`                          |
| 6 Eligibility  | `src/06_eligibility.py`  | `flagged.parquet`                            |
| 7 Publish      | `src/07_publish.py`      | files in `out/`                              |

Outputs in `out/`:

- `constituencies/csv/` and `constituencies/xlsx/`: one file per constituency with at least one flagged property, named `{constituency_code}_{constituency_name}`. CSV files begin with notice lines and a blank line before the header row. XLSX files have a "Notice" sheet and a "Properties" sheet.
- `national_summary.csv`: counts by status for each constituency.
- `constituency_index.json`: codes, names, counts and file names.
- `run_report.md`: row counts by stage, rejected rows, match rate, test result, Earley benchmark, plausibility check and spot-check sample.

`data/raw/`, `data/work/` and `out/` are git-ignored. The run report contains VO data, so do not publish it either.

## Data notes

- Records are asterisk-delimited, with 28 fields as set out in the VOA specification (Part two) plus a trailing asterisk. Column names come from the specification.
- **Rateable value is item 18** in the specification. The data confirms this: the field is numeric, and its values match the property descriptions. "Column 18" is right when counting from 1, and column 17 when counting from 0.
- **Firm name is item 9.** It is filled in on 76,913 of 2,178,394 rows (3.5%), mostly utilities and telecoms operators.
- Rows with a blank rateable value are, according to the specification, proxy records for deleted properties. They are rejected with that reason.

## Status definitions

Each row in a constituency file is flagged under at least one of the two columns.

`status_now` (rules in force today):

| Status                  | Meaning                                                                                                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `likely_eligible_now`   | Rateable value £12,000 or less, and no other properties found under the firm name. Usually this is because the firm name is blank, and the reason says so.             |
| `possibly_eligible_now` | Rateable value £12,001 to £14,999 (tapered relief), or £12,000 or less where the firm name appears on other properties that may meet the multiple-property conditions. |
| `not_flagged`           | Rateable value £15,000 or more or £0, or other properties under the same firm name break the multiple-property conditions.                                             |

`status_from_apr_2027` (announced rules, not yet in regulations) uses the same statuses, with the 2027 aggregate limit, plus:

| Status                        | Meaning                                                                                                                                                           |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `eligible_from_apr_2027`      | Mapped to retail, hospitality or leisure, with rateable value above £12,000 and below £21,000. The status means potentially eligible; the name follows the brief. |
| `excluded_possible_vape_shop` | Possibly a vape shop, which would otherwise be flagged. Vape shops are announced to lose SBRR.                                                                    |

Possible adult gaming centres use the general £12,000 and £15,000 thresholds in the April 2027 view.

The `reason` column explains each status, for example: "Now: Rateable value £11,500 is £12,000 or less. No other properties found under this firm name. From 1 April 2027: No change."

The "now" view applies to every property type. It includes properties that few people would think of as small businesses, such as advertising rights, telecoms masts and parking spaces. The `sector` column helps to filter these out.

## Thresholds

All thresholds are in `config/rules.yaml`. The code does not hard-code any of them.

| Rule                                         | Value                                                                        | Status                                            |
| -------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------- |
| SBRR full relief                             | rateable value up to £12,000                                                 | In force                                          |
| SBRR taper                                   | linear to nothing at £15,000                                                 | In force                                          |
| Each additional property                     | £2,899 or less                                                               | In force                                          |
| Aggregate limit before April 2027            | £19,999 outside London, £27,999 in London                                    | In force until 31 March 2027                      |
| Aggregate limit from April 2027              | £29,999, England-wide                                                        | Announced 28 October 2026; not yet in regulations |
| Retail, hospitality and leisure full relief  | up to £18,000, tapering to nothing at £21,000, 1 April 2027 to 31 March 2029 | Announced; not yet in regulations                 |
| Vape shops excluded from SBRR                | from 1 April 2027                                                            | Announced; definition not published               |
| Adult gaming centres keep general thresholds | from 1 April 2027                                                            | Announced; definition not published               |

Taper: relief = 1 − (rateable value − full relief limit) ÷ (taper end − full relief limit). This gives 50% at £13,500 under the general rule, and 50% at £19,500 under the 2027 retail, hospitality and leisure rule.

### Aggregate limit: ambiguity

Councils describe the aggregate limit as the total rateable value across **all** of a business's properties. The MHCLG letter words it as applying to second and further properties. This tool treats it as the total across all properties, including the one being assessed, which is the stricter reading. If the other reading is right, some multi-property rows marked `not_flagged` could qualify.

## Sector mapping (awaiting human review)

Sector is decided by three files in `mapping/`, in this order:

1. `text_flags.csv`: text patterns. This is the only way to find possible vape shops, because no VO code exists for them, and it finds very few. It also picks out dance schools, which are usually coded as schools.
2. `scat_overrides.csv`: the VOA SCAT code (item 22). It splits miscellaneous codes, for example gyms from stables within LX, and catches excluded uses such as banks and vets.
3. `sector_map.csv`: the 119 primary description codes from Appendix 2 of the VOA specification.

The target definition is SI 2025/1093. Each row has a `confidence` (high, medium or low) and `notes`. **Every row is marked `awaiting_review`.** Until a named reviewer changes every row to `signed_off`, stage 7 output is a draft, and every file says so. See `DECISIONS.md` for the reasoning, and `data/work/sector_coverage.csv` for counts by code.

## Wales

Wales has separate relief rules and is out of scope. Properties are assigned to Wales by billing authority code (6805 to 6955, VOA specification Appendix 1) and excluded at stage 3. The run report gives the count: 127,771 rows in the raw epoch 0004 file.

## London

London properties are identified by billing authority (the 33 London billing authorities). The higher aggregate limit before April 2027 depends on the billing authority. The run report gives the cross-check against the ONSPD London region.

## Tests

`tests/test_eligibility.py` uses small hand-built cases. It covers every threshold boundary (£12,000, £12,001, £14,999, £15,000, £17,999, £18,000, £21,000), the taper formula, the multiple-property limits, the London difference, the vape shop and adult gaming centre rules, a check that thresholds are read from config, and a check that reasons never claim relief.

## Out of scope for version one

A website, Wales, matching against council relief records, and automatic refresh from VO change files. A static constituency-search page over `out/constituency_index.json` is a possible second phase, but only if the licence position allows it.
