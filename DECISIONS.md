# Decisions

Judgement calls made while building version one. Each one is open to review.

## Source data

1. **File used.** The 2026 list entries baseline: `uk-englandwales-ndr-2026-listentries-compiled-epoch-0004-baseline-csv.zip`, epoch 0004 (file dated 1 October 2026, latest record date 29 September 2026). If more than one baseline zip is in `data/raw/`, the highest epoch is used. The historic entries file in the same zip is not used.
2. **Column layout.** Records have 28 fields, as in the specification (Part two, "List entry data items"), followed by a trailing asterisk. This gives an empty 29th field. Stage 1 stops if that field ever holds data, or if the line count differs from the row count.
3. **Rateable value is item 18.** The specification and the data agree. "Column 18" is correct if columns are counted from 1. Counted from 0, it is column 17.
4. **Deleted-property proxy records.** The specification says that rows with a blank rateable value are proxy records for deleted properties, not list entries. There are 34,858 of them. Stage 2 sends them to `rejected_rows.csv` with that reason.
5. **£0 rateable values** (9,746 rows) are kept but never flagged. There is no bill to relieve, so they cannot be "missing out".
6. **Property reference.** `property_reference` in the outputs is the UARN (item 7), the VOA's unique key for a property. The billing authority's own reference (item 4) is in `data/work`. It is not in the constituency files.

## England, Wales and London

7. **England and Wales are separated by billing authority code**, using Appendix 1 of the VOA specification (`mapping/billing_authorities.csv`). Welsh codes are 6805 to 6955. The billing authority, not the postcode, decides which country's relief rules apply. Welsh billing authority rows with an English postcode (45) are excluded. English billing authority rows that ONSPD places in Wales or Scotland (27) are kept but get no constituency, so they appear in no constituency file.
8. **London is identified by billing authority** (codes 5030 to 5990, 33 authorities). The aggregate limit depends on the billing authority. The ONSPD region is used only as a cross-check, and the run report gives the disagreements. The outputs include an `is_london` column, as agreed.
9. **Constituencies** are the 2024 Westminster constituencies (`pcon24cd`) from ONSPD August 2026. Names come from the `Documents/PCON ... names and codes` file in the same zip. Matches to terminated postcodes are kept, because ONSPD still holds their geography.

## Sector mapping

10. **The primary description code is too coarse on its own.** No VOA code identifies vape shops. Adult gaming centres share code LT1 with family entertainment centres. The miscellaneous codes (CX, LX, MX and others) each cover both qualifying and non-qualifying uses. Version one therefore uses three files, which the human agreed to (highest precedence first):
    - `mapping/text_flags.csv`: regular expressions on description text, and for vape shops also firm name and property name.
    - `mapping/scat_overrides.csv`: overrides by SCAT code (item 22, first three digits). Each override applies to one primary code, or to any code where the code is `*`.
    - `mapping/sector_map.csv`: one row for each of the 119 primary description codes in Appendix 2 of the specification.
11. **Primary and secondary codes.** The description code in the list is a primary code plus an optional secondary letter (W, S, C or O), as Appendix 2 describes. Every code in the epoch 0004 data resolves to one of the 119 primary codes.
12. **Mapping basis.** SI 2025/1093: regulation 3 (qualifying purposes), Schedule 1 (excluded purposes) and Schedule 2 (cultural, community and recreational facilities). Examples: banks, betting shops, car parks, marinas, crematoria, vets, show homes, recording studios and conference centres are mapped to `other`. Self-catering holiday units (CH1) are `hospitality` under regulation 3(1)(d). Public houses are `pub`. Wine bars are `hospitality`.
13. **Confidence.** `high` means the code or SCAT matches a purpose named in the SI. `medium` means the use usually qualifies but often does not. `low` means the meaning is unclear or the code mixes uses. No codes were invented. Every SCAT group of 5 or more properties whose sector came from the primary code alone was reviewed against the epoch 0004 data, and an override was added wherever the SCAT code gives a different or more certain sector. Wildcard (`*`) overrides are used only where the SCAT meaning holds whatever the primary code. Serviced offices (723) are limited to office codes, because a wildcard turned cafes and salons in serviced buildings into `other`.

    Judgement calls in the full review: vehicle repair workshops (CG1, SCAT 289, 16,772 properties) are retail, medium: repairs for visiting customers are a service under regulation 3(1)(a)(ii), but trade-only workshops cannot be told apart. Commercial garages (SCAT 113) are other. Community day centres (SCAT 067) are leisure, medium: care day centres would not qualify. Beach huts (LH1) are other, low: most are private, and none are above £12,000, so no April 2027 status changes. Dance schools are found by a text flag, because they are usually coded EP (school) under unrelated SCAT codes.
14. **Sign-off.** Every mapping row has `review_status = awaiting_review`. A named person, to be agreed, should review each row and change it to `signed_off`. Until every row is signed off, stage 4 logs a warning, every output file carries a "draft mapping" notice, and the run report says the mapping is awaiting review.

## Firm names and multiple properties

15. **The firm name field is sparse.** It is filled in on 76,913 of 2,178,394 rows (3.5%), mostly utilities and telecoms operators. For most small businesses, other properties cannot be checked.
16. **Normalisation.** Firm names are converted to lower case. `&` becomes `and`, punctuation becomes a space, and `limited` becomes `ltd`. Whitespace is collapsed. Placeholder names are treated as blank: occupier or owner variants, `unknown`, `vacant`, `void`, and generic words such as `shop`, `unit`, `mast` and `office`. Single characters are also treated as blank.
17. **Grouping scope.** Grouping is national (England only), because the SBRR multiple-property conditions apply to all of a ratepayer's properties in England. Counts within each billing authority are also calculated and kept in `data/work`.
18. **Multiple-property test.** Where a name appears on more than one property, the test checks two things: whether every other property under that name is £2,899 or less, and whether the combined value is within the aggregate limit. A pass gives `possibly_eligible_now`. A fail gives `not_flagged`, with a reason saying that name matching does not prove common ownership. The brief's general rule ("other properties" leads to "possibly") was applied only where the data cannot settle the test.
19. **Aggregate limit.** This is treated as the total across all properties, including the one being assessed, as `config/rules.yaml` says. The README notes the ambiguity in the wording.

## Eligibility

20. **Two views.** Each property gets `status_now` and `status_from_apr_2027`. Both use rateable values from the 2026 list.
21. **Retail, hospitality and leisure from April 2027.** Properties at or below £12,000 keep the general statuses (`likely_eligible_now` or `possibly_eligible_now`), as the brief's status vocabulary requires. Properties above £12,000 and below £21,000 are `eligible_from_apr_2027`, unless the multiple-property test fails.
22. **Possible vape shops** are assessed as retail first. If that would flag them in the April 2027 view, they become `excluded_possible_vape_shop`. A large vape shop that would not be flagged anyway stays `not_flagged`, so it does not appear in the outputs only because of the exclusion. Vape shops are not excluded in the "now" view.
23. **Possible adult gaming centres** use the general £12,000 and £15,000 thresholds in the April 2027 view.
24. **Reasons.** Each row has one `reason` that combines both views: "Now: ... From 1 April 2027: ...". When the April 2027 text is the same as the "now" text, it reads "No change."

## Outputs

25. **Extra columns.** The constituency files add `billing_authority` (the notice tells readers to check with the billing authority) and `is_london` (agreed with the human) to the schema in the brief.
26. **Notice in CSV files.** The notice lines come first, then a blank line, then the header row. Anyone reading the CSV by program should skip to the row that starts with `constituency_code`. XLSX files have a separate "Notice" sheet.
27. **Earley benchmark.** Reading East no longer exists under the 2024 boundaries. The benchmark uses the RG6 district within Earley and Woodley, and shows all of RG6 alongside. Two extra definitions are reported for context. Nothing was tuned to the "just under 100" figure.
28. **Plausibility check.** The run report gives the share of retail, hospitality and leisure properties at £18,000 or less, and the count at £12,001 to £18,000. It describes a share outside 40% to 85%, or a count outside 35,000 to 200,000, as a large gap. These bounds are only for wording the report. They do not affect any status.

## Licence

29. **The VO licence conflicts with the intended use.** The VO terms limit use to non-domestic rating purposes and restrict onward disclosure. Giving files to MPs' offices and campaigners may fall outside those terms. As agreed with the human, the tool was built with this warning in the README and in every output file. Outputs stay local and git-ignored. Nothing should be distributed until the VO has confirmed in writing (ccaservicevo@hmrc.gov.uk) and data protection advice has been taken.
