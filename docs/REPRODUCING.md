# Reproduce and deploy

This guide distinguishes **running the published website** from **rebuilding the analysis**. The committed `web/dataset/` is a publication snapshot; raw inputs and intermediates are excluded from Git.

## Run the published website

Requires Node.js 22+ and Python 3.11+ on PATH. Clone the [CampaignLab repository](https://github.com/CampaignLab/Nationwide-Business-Rates-Relief-Finder), open its root, then run:

```sh
npm test
npm run build
npm run dev
```

Open <http://127.0.0.1:3000/>. `npm run dev` serves `web/` with Python; `npm run build` writes the deployment to `dist/`. No npm packages, account credentials or API keys are required to use the local website. `npm test` also exercises the build. To serve the exact built files, use:

```sh
python -m http.server 3000 --directory dist --bind 127.0.0.1
```

If Python is installed as `python3`, use that executable instead. For the source website, `python3 -m http.server 3000 --directory web --bind 127.0.0.1` is equivalent to the dev command.

## Set up the analysis environment

Use a Python virtual environment and install the pinned requirements. The commands below assume Python 3.11+ is available as `python`.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force data/raw | Out-Null
```

### macOS/Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p data/raw
```

The pipeline uses DuckDB, openpyxl, PyYAML and pytest. Downloads, expanded inputs and intermediate data require several GB of local storage. The POSIX `Makefile` is an optional convenience; Windows users can use the explicit commands above.

## Obtain the exact source snapshots

Read the provider terms and obtain these ZIPs separately:

| File in `data/raw/` | Source |
|---|---|
| `uk-englandwales-ndr-2026-listentries-compiled-epoch-0004-baseline-csv.zip` | [VOA rating-list downloads](https://voaratinglists.blob.core.windows.net/html/rlidata.htm) |
| `ONSPD_AUG_2026.zip` | [ONS Open Geography Portal](https://geoportal.statistics.gov.uk/); August 2026 postcode directory |

Use the **current list entries baseline**, not summary valuations, a weekly changes file or the historic-entry CSV inside the archive. Do not unzip/rename the source inputs manually; the pipeline selects the required members. Keep only the intended snapshots in `data/raw/`: the code chooses the highest VOA epoch and latest ONSPD release if multiple matching files are present.

If the provider no longer offers an old snapshot, reproducing this exact publication requires an independently retained lawful copy. A newer file is a new analysis, not an exact reproduction. The pipeline does not automatically apply weekly change files or download updates.

The [source manifest](SOURCES.json) records the archive sizes and SHA-256 checksums actually used. Compare downloaded files with it before claiming an exact reproduction. It also pins the analysis commit; checking out that commit preserves the same rules, mappings and supplied-name inputs.

Name, use-warning, council and benchmark CSVs in `mapping/` are already committed. The full comparison workbook is not required to run the pipeline.

## Run the pipeline

Windows:

```powershell
.\.venv\Scripts\python.exe run_all.py
```

macOS/Linux:

```sh
.venv/bin/python run_all.py
```

The runner first executes the Python tests, then stops at the first failed stage. It writes intermediate Parquet files and stage logs to `data/work/`, and outputs to `out/`. A full run regenerates those outputs; preserve an older run in a separate checkout/folder if it is needed for comparison.

| Stage | Responsibility |
|---|---|
| 01 | Parse the fixed VOA layout, check record counts and record metadata |
| 02 | Normalise/cast values; retain missing postcodes; reject deleted-property proxies |
| 03 | Select English billing authorities and match exact ONS constituency geography |
| 04 | Apply version-controlled sector mappings and text flags |
| 05 | Group normalised firm names as potential multiple-occupation clues |
| 06 | Calculate the earlier modelled relief/status fields |
| 06b | Add conservative screening, supplied-name provenance, council links and comparison outputs |
| 07 | Publish constituency CSV/Excel files, index, summaries and internal run report |

`out/run_report.md` is an internal diagnostic report, not one of the staged public files. The screening report and comparison are deliberately publishable supplements. See [Data dictionary](DATA_DICTIONARY.md).

## Stage a rebuilt dataset

The stage command refuses to overwrite `web/dataset/`. That folder is already present in a normal clone. Move it aside before staging the new output; the following commands preserve the old snapshot instead of deleting it. Choose an unused backup name on a later run.

Windows:

```powershell
New-Item -ItemType Directory -Force .tmp | Out-Null
Move-Item -LiteralPath web/dataset -Destination .tmp/dataset-before-rebuild
node scripts/prepare-data.mjs out --include-downloads
node scripts/verify-published.mjs
npm test
npm run build
```

macOS/Linux:

```sh
mkdir -p .tmp
mv web/dataset .tmp/dataset-before-rebuild
node scripts/prepare-data.mjs out --include-downloads
node scripts/verify-published.mjs
npm test
npm run build
```

With `--include-downloads`, staging copies the index, constituency CSV/Excel files and named public supplements. Without it, only summaries are staged. The default verifier expects a complete property publication; use the full mode for this project's public release.

## Release checklist

Regenerate the public SCAT reasoning table after mapping changes, with
`python scripts/classification_audit.py` from the project root and DuckDB installed.
Keep `data/work/sectored.parquet` available to include observed code pairs. The script
updates the methodology HTML and CSV/JSON supplements in web/dataset and out.
Without the intermediate it covers documented mappings/reference codes only; verify
coverage before publishing. Commit the generated page and three named supplements.

1. Record the exact source ZIPs, dates, policy assumptions and changes. Review mapping changes and all 96 Earley benchmark outcomes. Do not tune results to match an old count.
2. Run Python tests, Node tests and `node scripts/verify-published.mjs`. Reconcile likely/review/unassigned totals and inspect changed records. A passing test suite does not establish actual entitlement.
3. Update `README.md`, `docs/METHODOLOGY.md`, `web/methodology.html` and `CHANGELOG.md` together. Preserve provider terms, uncertainty and name provenance.
4. Check the Git diff for raw data, credentials, local paths and unintended property publication. Staged property files are deliberately tracked; if new ignored files need publication, add only those intended paths explicitly. Raw/intermediate inputs stay ignored.
5. Deploy a preview in the existing authorised Vercel project, check public downloads and the browser flow, then promote the tested deployment. Retain the previous production deployment for rollback.
6. Confirm the source commit is pushed and the production URL serves the intended snapshot. Record the deployment IDs and checks with the release record.

The existing Vercel project is `business-rates-relief-finder` in the `campaign-lab` team. It uses framework **Other**, `npm run build`, output **dist**, repository root **.**, and Node 22.x. Deployment requires separate Vercel authentication/permission; local use does not. Automatic Git deployment should not be assumed—the current publication was deployed through the CLI.

The public URL is <https://business-rates-relief-finder-campaign-lab.vercel.app/>. Inspect the intended team/project before deploying; the code alone does not authorise publication to another destination.

## Changes that need special care

- **New VOA/ONSPD release:** verify the schema, boundary geography and retained benchmark references before rebuilding. Missing benchmark references currently stop stage 6b and need an explained migration.
- **New policy guidance:** update the dated configuration and relevant tests; the website does not ingest guidance automatically.
- **Council changes:** refresh the official-directory mapping by VOA code, documenting successor exceptions; never infer the council from constituency.
- **New names/use evidence:** retain original fields, source/date/status and record why a warning is added or removed. Changing the supplied trading name alone must not establish eligibility.
