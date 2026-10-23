# OULAD Data Quality Decisions

## Scope and status

This document records the audit of the downloaded OULAD archive and the decisions used to prepare interactions for the project. Raw source files remain unchanged. The preparation script is committed in `scripts/prepare_interactions.py`; the Django importer and database validation described in the architecture currently belong to development work not yet merged into `main`.

## Missing values

Missing values are not globally imputed during source preparation. Treatment depends on meaning and analysis.

- `studentInfo.imd_band`: retain missing. For ML, compare an explicit `Unknown` category with train-only imputation and validate the choice.
- `studentRegistration.date_unregistration`: retain missing because absence of a recorded unregistration is meaningful.
- `assessments.date`: retain missing exam dates; do not invent dates.
- `studentAssessment.score`: retain missing scores. Missing is not equivalent to score 0. In the audited archive, 173 missing scores are associated with TMA records.
- `vle.week_from` / `week_to`: retain missing until an analysis requires these fields.

For predictive modelling, any learned imputation must be fitted on training data only. The imputer and any missingness indicator must not learn from validation/test data.

## `studentVle.csv` duplicates and Interaction grain

`DataFrame.drop_duplicates()` compares all columns by default. Therefore rows with different `sum_click` are not exact duplicates. `drop_duplicates(subset=[...])` would impose a business key and can discard observations.

Audit of the downloaded raw file:
- Raw rows: 10,655,280.
- Exact duplicate rows beyond their first occurrence: 787,170.
- Rows after exact de-duplication: 9,868,110.
- Student-resource-day keys occurring more than once: 1,614,505.
- Repeated keys containing more than one distinct `sum_click` value: 1,179,074.
- Unique student-resource-day keys after aggregation: 8,459,320.

Therefore, do not use subset-based duplicate deletion. Exact duplicates are removed as redundant source rows; repeated keys are handled by an explicit application grain.

### Final `Interaction` grain

One processed `Interaction` record represents:

> one student + one course presentation + one VLE resource + one day.

The business key is:

`(code_module, code_presentation, id_student, id_site, date)`

Processing:
1. Keep the raw OULAD file unchanged.
2. Remove only exact duplicate rows.
3. Group by the five fields above.
4. Sum `sum_click` within each group.
5. Store the result as `total_clicks` in the processed interaction data.

This is **aggregation, not duplicate deletion**. For example, 4, 1, and 8 clicks for the same student/resource/day become 13 total clicks.

Recorded counts:
- 9,868,110 rows after exact de-duplication.
- 8,459,320 processed interaction rows after aggregation.
- 20.61% reduction from the raw row count.
- 14.28% reduction from the exact-deduplicated row count.

## Domain validation

- `studentAssessment.score` should be in [0, 100]; no invalid values were found in the audit.
- `assessments.weight` should be in [0, 100]; no invalid values were found.
- `studentVle.sum_click` is a non-negative count; no negative values were found.
- After aggregation, `total_clicks` remains non-negative; the minimum observed value is 1.

A passed validation rule is retained as a regression check; there is nothing to “fix” when the source already satisfies the rule.

## Modelling and leakage

`studentInfo.final_result` is an outcome, not an early-warning feature. Predictive features must only use information available at the intended prediction time. Future assessments, interactions, or registration information must not leak into earlier prediction windows.

## Reproducible preparation

`scripts/prepare_interactions.py` reads `studentVle.csv` from the raw OULAD ZIP, removes only exact duplicates, aggregates the agreed student-resource-day grain, and writes the processed interaction table. Source and processed row counts are printed so the transformation can be audited.

## Remaining work

The interaction preparation and source audit are complete for the audited archive. Automated tests for the preparation script and the full Django import/relational integrity checks remain to be committed and run from the repository. The five-model development design and current API are documented in [architecture.md](architecture.md); they are not yet present on `main`.
