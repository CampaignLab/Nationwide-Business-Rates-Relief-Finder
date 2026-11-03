# Business Rates Relief Finder

A static constituency browser and reproducible Python/DuckDB pipeline for candidate property assessments in England. The existing CampaignLab Vercel site publishes an explicitly staged dataset; without one the app displays synthetic demonstration data.

## Run and publish

Requires Python 3.11+ and Node.js 22+. Put the VOA baseline ZIP and ONSPD ZIP in `data/raw/`, install `requirements.txt` in a virtual environment, then run:

```sh
python run_all.py
npm test
node scripts/prepare-data.mjs out --include-downloads
npm run build
```

The prepare command refuses to replace an existing `web/dataset` folder; move it aside before rebuilding. `npm run dev` serves the browser locally on port 3000. Build output is `dist`, suitable for the existing Vercel project with framework Other and build command `npm run build`. No API keys, database or npm dependencies are required.

Only allowlisted browser files and explicitly staged data enter the build. Raw data, environment files and the internal run report are excluded. Publication files are deliberately force-added to Git after validation; source inputs stay ignored. To validate a staged release run `node scripts/verify-published.mjs`.

The browser supports constituency/region search, default likely-candidate results, a separate review view, RV filters, name/postcode/reference search and filtered CSV downloads. The complete constituency CSV/Excel files contain both candidate and review records, with notices. Locally selected output folders are read in the browser without uploading. The table shows up to 100 matches; downloads contain all filtered matches.

## Reproducibility and interfaces

The complete pipeline retains original assessments, adds legacy modelled eligibility, then adds `screening_outcome` (`likely_candidate`, `needs_review`, `outside_target`), `screening_reason`, `review_reasons`, name provenance and billing-council links. The publisher exports likely/review records with an exact English constituency; `unassigned_review.csv` retains unresolved locations. The index's legacy `target_new_full_relief` count now counts all exported screening records; the per-property legacy flag retains its original modelled meaning. New consumers should use the separate `likely_candidate` and `needs_review` counts.

Source downloads: [VOA rating lists](https://voaratinglists.blob.core.windows.net/html/rlidata.htm) and ONS Open Geography Portal. Mapping/rule changes require a rebuild; ONSPD schema changes may require updating `ONSPD_FIELDS`. Archived publication counts are in `config/previous_publication.json`. Revisions to rules, mappings, supplied names and council links are version controlled.

## Candidate screening

The public finder now separates **Likely candidates** from **Needs review** for English property assessments with £12,000 < RV ≤ £18,000. These are automatic screening outcomes for the announced April 2027 expansion, not council awards or proof that a bill newly becomes £0. The original eligibility fields remain modelled results for compatibility; use `screening_outcome` and `screening_reason` for the new views.

Specific qualifying premises descriptions without detected conflicts enter the main list. Generic shops, conditional uses, possible exclusions, terminated/unmatched postcodes and possible multiple-property name matches require review. Clear non-RHL uses are outside target. Missing names do not by themselves exclude a property. Recreational marinas are considered; unspecified marinas need review. Firm-name equality never proves a shared ratepayer.

VOA firm names are preserved. The optional `mapping/researched_names.csv` supplies trading names with source, recording date and verification status. The imported Earley spreadsheet names are unverified display information, never eligibility evidence. Per-property use concerns are recorded separately with sources. Council links come from `mapping/council_links.csv`, keyed by VOA code; official homepages are taken from the government's Planning Data authority directory using address-custodian identifiers and documented successor exceptions. Refresh this directory when councils change.

Run `run_all.py` to test and rebuild, including stage `06b_screening` between eligibility and publication. Missing/malformed postcodes are retained for unassigned review; assessments without a usable RV are rejected with reasons. `out/screening_report.json` reconciles national outcomes, legacy results and the previous publication. `out/earley_comparison.csv` records all 96 distinct comparison assessments (64 spreadsheet, 88 old live list, 56 shared). Neither old list is ground truth.

The website defaults to likely candidates in each constituency. Full CSV/Excel downloads contain both candidate and review records; the browser's filtered download contains only the selected view and filters, with the disclaimer. Unassigned review records are a separate national download. Counts are property assessments, not verified businesses. Source data is fixed to VOA epoch 0004 (1 October 2026) and ONSPD August 2026 for this comparison. The rule snapshot is 28 October 2026, announced and not yet in regulations.

Read the [public methodology](https://business-rates-relief-finder-campaign-lab.vercel.app/methodology.html) for the full process, source links, comparison and limitations. Before making a definitive statement to a business, confirm occupation, ratepayer identity, other properties, existing relief and the final bill with its billing council. For an unverified case, use “this property may qualify; please check with your council”.

---


## Data use and interpretation

The [VO download guidance](https://voaratinglists.blob.core.windows.net/html/rlidata.htm) states that the data is supplied under a restricted licence, not the Open Government Licence. It permits passing data to third parties subject to communicating the terms. The [VO terms](https://www.tax.service.gov.uk/business-rates-find/terms-and-conditions) restrict use to the stated non-domestic rating purposes and onward disclosure to those purposes; personal data is outside that permission. Public availability therefore does not establish unrestricted reuse. A public website is not categorically prohibited: whether its particular use and redistribution fit the terms needs to be assessed. In particular, rating-assessment assistance and campaign outreach are different purposes. Aggregate outputs should also be assessed rather than assumed exempt.

Generated files retain source-term notices and methodological disclaimers. This web layer does not determine the licence position or grant permission to distribute a dataset.

Potential eligibility is based on rateable value and property type. The tool cannot establish occupancy, the ratepayer, relief currently received or every property held by an occupier. Check with the billing authority. Sector mappings may await human review; April 2027 statuses reflect the rule snapshot in the dataset. The pipeline covers England.
