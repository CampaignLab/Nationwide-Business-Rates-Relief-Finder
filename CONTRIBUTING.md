# Contributing and correcting records

Start with the [methodology](docs/METHODOLOGY.md), [current design decisions](DECISIONS.md) and [reproduction guide](docs/REPRODUCING.md).

## Report a property or mapping problem

Open a [GitHub issue](https://github.com/CampaignLab/Nationwide-Business-Rates-Relief-Finder/issues) with the VOA property reference, the field or outcome concerned, a dated public evidence link where available, and the proposed correction. State whether the concern is the premises use, identity, postcode, council link or policy interpretation.

Do not put private ratepayer account numbers, personal contact details, bills or other confidential council documents in a public issue. A trading name or a matching firm name is not proof of legal occupation or entitlement. For an actual relief decision, use the billing council's business-rates service.

## Propose a change

- Keep original VOA fields intact. Record supplied names in `mapping/researched_names.csv` with source, recording date and verification status. Keep eligibility/use evidence separate in `mapping/property_review_evidence.csv`.
- Explain the guidance behind a sector-map or policy change. Do not mark mapping rows `signed_off` simply to suppress a warning; formal review is still outstanding.
- Use the 96-reference Earley comparison to investigate changed outcomes, not as a target count to reproduce. Report false-positive and false-negative risks.
- For code or rule changes, run the relevant Python and Node checks and regenerate the affected outputs. Show outcome/count changes and source snapshots in the pull request.
- For documentation-only changes, check internal links, run `npm test`, inspect the built methodology page, and confirm that no data or classification changes slipped into the diff.

## Release discipline

Keep raw input ZIPs, intermediate files, local environment files and credentials out of Git. Published property files are deliberately tracked only after review. Document source/rule dates, verification results and changes in `CHANGELOG.md`; update the repository and website methodology together. Follow the [release checklist](docs/REPRODUCING.md#release-checklist).
