# Business Rates Relief Finder

A Vercel-ready constituency browser alongside the existing Python/DuckDB processing pipeline. The website starts with **synthetic demonstration data**. No real property data is included or deployed.

## Which properties this version selects

The primary outputs now select **English RHL properties with rateable values strictly above £12,000 and up to £18,000 inclusive** that pass the modelled conditions for full SBRR from **1 April 2027**. This is the group potentially moving from partial/no SBRR to full relief under Budget 2026. Exactly £12,000 is excluded because it was already in the full-relief band; exactly £18,000 is included. Properties above £18,000 in the new taper band are excluded from this target list, as are non-RHL premises, possible vape shops, possible adult gaming centres and properties failing known multiple-property checks.

The underlying assessment retains both the old and new rules for all properties. Stage 6 writes a `target_new_full_relief` flag; stage 7 uses it for the constituency CSV/XLSX files and target counts. The index identifies the cohort explicitly, and the website rejects older broad indexes rather than labelling them as this target group. Rerun stages 6 and 7 (or the whole pipeline) and re-prepare the website dataset after updating. Do not reuse the old generated files.

Properties above £12,000 and below £15,000 may already get tapered relief; properties from £15,000 to £18,000 were outside the old SBRR band. Both are included. Counts are **properties, not unique businesses**, and the snapshot does not establish actual receipt, occupancy or every occupier's property holdings. Sector mappings are still subject to their review status. These are potential beneficiaries, not confirmed awards or bill-saving estimates.

Policy sources: [Budget 2026](https://www.gov.uk/government/publications/budget-2026-document/budget-2026-html) and the [MHCLG technical annex, SBRR paragraph 5](https://www.gov.uk/government/publications/82026-details-of-the-budget-package-and-the-multipliers-for-20272028/82026-details-of-the-budget-package-and-the-multipliers-for-20272028). Thresholds remain in `config/rules.yaml`.

## Run the website

Requires Node.js 22+ and Python 3.11+ (Python is used only for the local preview server).

```sh
npm test
npm run build
npm run dev
```

Open http://127.0.0.1:3000. No npm dependencies, database, API keys or environment variables are required. Search by constituency name or code, filter by region, and browse potential-relief counts.

## Deploy on Vercel

1. Import this GitHub repository into a Vercel project.
2. Use the repository root, framework preset **Other**, build command `npm run build`, and output directory `dist` (also specified in `vercel.json`).
3. Deploy. The site opens with the synthetic demo immediately.

The build copies five browser files and an optional explicitly prepared publication dataset. It does not run the data pipeline or automatically publish `data/`, `out/` or reports. `.vercelignore` excludes raw pipeline inputs and outputs from deployment uploads. Vercel Hobby is for personal, non-commercial use; choose an appropriate plan for organisational use.

## Publish a real dataset

After generating outputs, prepare the constituency index for public browsing:

```sh
npm run prepare-data -- out
npm run build
```

This stages summary counts only, with no property downloads. To also stage the original CSV/XLSX property files, use `node scripts/prepare-data.mjs out --include-downloads`. The site automatically loads the staged dataset instead of the demo. Where a CSV is available, **View properties** opens a search by address, postcode, firm name or property reference, showing rateable values, both eligibility statuses and the original reasons. Only flagged properties are included; a missing property does not establish ineligibility. The browser limits displayed matches to 100 at a time and browsable CSVs to 30 MB. Source paths are validated; reports and unrelated files are not copied. Review the intended use and publication contents against the source terms before deploying.

`web/dataset/` is git-ignored to avoid accidental commits. For a Git-based Vercel deployment, deliberately add the publication files using `git add -f web/dataset`, or stage them in a controlled build step. For a CLI deployment they must be present locally when deployed. The prepare command refuses to replace an existing staged folder; move that folder aside before preparing a replacement.

## Browse your generated results

On the website, choose **Choose output folder** and select the pipeline's `out/` directory. The app reads `constituency_index.json`, then links matching files under `constituencies/csv/` and `constituencies/xlsx/`. File selection is local to the user's browser: there is no upload endpoint or persistent browser storage. Refreshing clears the dataset. Folder selection requires a browser with directory-input support, such as current Chrome or Edge.

The index comes from `src/07_publish.py` and includes the target-cohort definition. Counts refer to the constituencies represented in that index; it includes only constituencies with target properties. Overall property counts cover all premises in those constituencies; the target counts and status breakdowns cover only the selected RHL cohort. The website shows the dataset's rule snapshot and mapping-review state. CSV/XLSX downloads are the original generated files, with their notices intact. No download is shown unless its matching file was selected.

This version supports static published datasets and browser-local datasets. It does not provide user accounts, remote uploads or online pipeline execution. Those need a separate data-access and processing design.

## Generate data with the existing pipeline

Install the pinned Python requirements in a virtual environment. Put the zipped VO 2026 rating-list baseline and zipped ONS Postcode Directory in `data/raw/`, then run:

```sh
python -m pip install -r requirements.txt
python run_all.py
```

The runner executes the existing eligibility tests and stages 1–7, stopping on failure. Input data is not included. Download the rating list from the [VO downloads page](https://voaratinglists.blob.core.windows.net/html/rlidata.htm), accepting its terms, and obtain ONSPD from the ONS Open Geography Portal. ONSPD schema changes may require updating `ONSPD_FIELDS` in `src/03_constituency.py`.

Outputs include per-constituency CSV/XLSX files, `national_summary.csv`, `constituency_index.json` and `run_report.md`. Rules live in `config/rules.yaml`; mapping review and methodology decisions are documented in `DECISIONS.md`. The assessment rules are retained; publication is narrowed to the new-full-relief RHL cohort.

## Data use and interpretation

The [VO download guidance](https://voaratinglists.blob.core.windows.net/html/rlidata.htm) states that the data is supplied under a restricted licence, not the Open Government Licence. It permits passing data to third parties subject to communicating the terms. The [VO terms](https://www.tax.service.gov.uk/business-rates-find/terms-and-conditions) restrict use to the stated non-domestic rating purposes and onward disclosure to those purposes; personal data is outside that permission. Public availability therefore does not establish unrestricted reuse. A public website is not categorically prohibited: whether its particular use and redistribution fit the terms needs to be assessed. In particular, rating-assessment assistance and campaign outreach are different purposes. Aggregate outputs should also be assessed rather than assumed exempt.

The existing pipeline's file notices take a more conservative position, asking for written VO confirmation and data-protection advice before sharing. Those notices are preserved in generated files; they are project guidance, not a verbatim statement of the licence. This web layer does not determine the licence position or grant permission to distribute a dataset.

Potential eligibility is based on rateable value and property type. The tool cannot establish occupancy, the ratepayer, relief currently received or every property held by an occupier. Check with the billing authority. Sector mappings may await human review; April 2027 statuses reflect the rule snapshot in the dataset. The pipeline covers England.

