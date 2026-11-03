# Design decisions

Current design as at **3 November 2026**. This replaces the initial decision log; earlier wording remains in Git history. [CHANGELOG.md](CHANGELOG.md) records the evolution. The [methodology](docs/METHODOLOGY.md) explains the public results.

## 1. Screen property assessments, not confirmed recipients

The VOA rating list supplies an assessment, recorded use and value. It does not supply a complete current ratepayer/occupation/relief account. We therefore publish candidates with explicit uncertainty rather than a definitive mailing list or a calculation of newly zero bills. An assessment is not necessarily one business.

## 2. Use a precise target band and a dated policy snapshot

The target is England, with **£12,000 < RV ≤ £18,000**, for the announced April 2027 RHL expansion. Exactly £12,000 is excluded from this target; exactly £18,000 is included. Taper cases above £18,000 are outside it. The assumptions in `config/rules.yaml` remain a dated announcement model, subject to the final regulations and guidance.

## 3. Separate the screening decision from the earlier relief model

Stages 1–6 retain the original modelled status and relief fields. Stage 6b adds `likely_candidate`, `needs_review` or `outside_target` and an explanation. These screening outcomes drive the new views and publication. A legacy field called `eligible_from_apr_2027` is not an award. The [data dictionary](docs/DATA_DICTIONARY.md) documents the compatibility fields and the index count whose historical name is retained.

## 4. Prefer review over confident classification of ambiguous records

Sector mapping uses description text flags, specific primary-code/SCAT overrides, wildcard SCAT overrides, then the primary description code. High mapping confidence is a judgement about the recorded classification, not a probability of receiving relief.

The additional screening step flags generic shops, conditional or mixed uses, possible exclusions and known property-specific concerns. Clear recorded non-RHL uses are outside target. Recreational marinas may qualify; unspecified marinas and moorings require review. All mapping rows currently await formal sign-off. The site and files disclose that status.

## 5. Use names as clues, with provenance

Original VOA firm names are preserved. National normalised-name groups can flag possible multiple occupation, but are not verified legal ratepayer matches. Missing names do not establish sole-property occupation or cause review by themselves. Even generic names can create spurious groups, so a group moves a candidate to review instead of proving failure.

Spreadsheet-supplied trading names are matched by the VOA property reference, labelled unverified and used for identification/display. They do not independently establish qualifying use or entitlement. Separate, sourced property-use warnings may affect screening.

## 6. Match constituencies exactly; derive the council from the source authority

English billing-authority codes determine the national rules. Postcodes are matched exactly to the ONS directory's 2024 constituency geography. There is no postcode-sector approximation. Missing/unmatched locations remain available for review. Terminated-postcode matches retain their geography but require review. English-billed assessments mapped outside an English constituency remain unassigned for publication.

Council links use VOA authority codes and a government directory, with named exceptions recorded in the methodology. A constituency does not determine the billing council. Links are directory-sourced homepages and have not all been individually tested for current service availability.

## 7. Preserve sources and make corrections inspectable

The published analysis uses fixed VOA/ONS snapshots so that changes in screening can be distinguished from changes in source data. Original source ZIPs and intermediate Parquet files are excluded from Git; explicitly staged publication files are committed. Supplied names, use warnings, rules and mapping edits are version controlled. Changes should include evidence and a dated explanation.

## 8. Treat comparisons as diagnostics

The independent 64-record spreadsheet and previous 88-record Earley list share 56 assessments. Their union of 96 references is a regression benchmark. Neither is ground truth, and no rule is tuned to recreate either count. The broader alternative repository models 2026/27 relief; like-for-like filtering was necessary before comparing it with the April 2027 target.

## 9. Preserve model caveats rather than claiming account-level accuracy

The legacy multiple-property model treats its aggregate RV limit as including the property being assessed. The announcement refers to second and further properties, so that interpretation remains an assumption. It is not used as proof of entitlement: the conservative screening layer treats multiple-name matches as review concerns. No savings, newly zero bill, current occupation or actual award is established by either layer.

## 10. Keep provider terms distinct from analytical limitations

The previous log contained a blanket instruction against distribution. That is superseded by the current public publication and [data-use notice](docs/DATA_USE.md), which links the provider's terms and does not assert a blanket permission or prohibition for all downstream uses. No written VOA endorsement or licence clearance is claimed. Public availability and analytical accuracy are separate questions.
