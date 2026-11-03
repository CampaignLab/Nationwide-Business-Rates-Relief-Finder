# Business Rates Relief Finder

Find English property assessments that may qualify for expanded full small business rates relief from **1 April 2027**. The finder screens retail, hospitality and leisure (RHL) premises with **£12,000 < rateable value ≤ £18,000** and separates clearer candidates from cases needing review.

**[Open the finder](https://business-rates-relief-finder-campaign-lab.vercel.app/)** · **[Read the methodology](docs/METHODOLOGY.md)** · **[What changed and what we found](CHANGELOG.md)**

This is an automatic screening tool. It does not establish the current occupier, their other properties, an actual relief award or whether a bill will newly become £0. Confirm individual circumstances with the billing council before making that claim. “Likely” describes a screening category, not a measured probability. Sector mappings remain draft.

## Use the results

1. Choose a constituency and open **View properties**. It starts on **Likely candidates**.
2. Use **Needs review** for ambiguous descriptions, conditional uses and other concerns. Each record explains its outcome.
3. Search by address, postcode, property reference or supplied name; filter by rateable value.
4. Use **Download filtered CSV** for the selected results. Constituency CSV/Excel links contain **both** candidate and review records. Names supplied separately from VOA are labelled with their source and verification status.
5. Follow the council link to find its business-rates team. An official council link is a route to confirmation, not confirmation itself.

## Published snapshot — 3 November 2026

| Screening result | Property assessments |
|---|---:|
| Likely candidates | 24,631 |
| Needs review, assigned to an English constituency | 90,614 |
| Needs review, without an exact English constituency match | 181 |
| Constituencies covered | 543 |

These counts use VOA 2026 epoch **0004**, dated **1 October 2026**, and **ONSPD August 2026**. The policy model uses the **28 October 2026 announcement**, marked announced and not yet in regulations in this release. The data and rules do not refresh automatically. Counts refer to assessments, not unique businesses.

## Understand and reproduce the work

| Document | What it covers |
|---|---|
| [Methodology](docs/METHODOLOGY.md) | Sources, selection rules, uncertainty and the spreadsheet comparison |
| [Reproduce and deploy](docs/REPRODUCING.md) | Installation, fixed input snapshots, pipeline stages, checks and releases |
| [Data dictionary](docs/DATA_DICTIONARY.md) | Download fields, file formats and legacy model fields |
| [Design decisions](DECISIONS.md) | Why we chose conservative screening and exact postcode matching |
| [Change history](CHANGELOG.md) | How the tool evolved and what the comparisons changed |
| [Data use and attribution](docs/DATA_USE.md) | Provider terms, provenance and corrections |
| [Contributing](CONTRIBUTING.md) | How to propose an evidenced correction or code change |

## Run the website locally

Requires **Node.js 22+** and **Python 3.11+**. There are no npm dependencies or required API keys.

```sh
npm test
npm run build
npm run dev
```

Open <http://127.0.0.1:3000/>. The checkout includes the published snapshot. Without a staged dataset, the site displays labelled synthetic demonstration data. The static build is written to `dist/`.

To rebuild the data, follow [Reproduce and deploy](docs/REPRODUCING.md). The full VOA and ONS source ZIPs and intermediate files are not committed.

## Repository guide

| Location | Purpose |
|---|---|
| `src/` | Python/DuckDB ingestion, geography, sector mapping, model and screening |
| `config/` | Policy assumptions and previous-publication counts |
| `mapping/` | Premises-use mappings, supplied names, evidence and council directory |
| `web/` | Static browser and explicitly published dataset |
| `scripts/` | Website build, dataset staging and publication checks |
| `tests/` | Python pipeline/rule tests and Node browser-data tests |
| `docs/` | Methodology, field reference and operational instructions |

The project builds on the [original ChrisOwen101 pipeline](https://github.com/ChrisOwen101/Nationwide-Business-Rates-Relief-Finder). We also compared the [alternative CampaignLab implementation](https://github.com/CampaignLab/business-rates-relief) and an independently prepared Earley and Woodley spreadsheet. The comparison is a diagnostic exercise, not independent confirmation of entitlement.

VOA data is supplied under its own restricted terms, not the Open Government Licence. Read [Data use and attribution](docs/DATA_USE.md) before reusing the published records.
