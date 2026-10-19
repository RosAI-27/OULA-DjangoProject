# OULAD Data Quality Decisions

## Scope

This document records Phase 2 validation decisions before loading OULAD into Django. Raw source files remain unchanged.

## Missing values

Missing values are not globally imputed during source preparation. Treatment depends on meaning and analysis.

- `studentInfo.imd_band`: retain missing. For ML, compare an explicit `Unknown` category with train-only imputation and validate the choice.
- `studentRegistration.date_unregistration`: retain missing because absence of a recorded unregistration is meaningful.
- `assessments.date`: retain missing exam dates; do not invent dates.
- `studentAssessment.score`: retain missing scores. Missing is not equivalent to score 0. In the current data, 173 missing scores are associated with TMA records.
- `vle.week_from` / `week_to`: retain missing until an analysis requires these fields.

For predictive modelling, any learned imputation must be fitted on training data only. The imputer and any missingness indicator must not learn from validation/test data.

## `studentVle.csv` duplicates and Interaction grain

`DataFrame.drop_duplicates()` compares all columns by default. Therefore rows with different `sum_click` are not exact duplicates. `drop_duplicates(subset=[...])` would impose a business key and can discard observations.

Audit of the provided raw file:

- 10,655,280 rows.
- 787,170 rows are repeated exact rows beyond their first occurrence (`df.duplicated().sum()`).
- 9,868,110 rows remain after exact de-duplication.
- 1,614,505 student-resource-day keys occur more than once.
- 1,179,074 repeated keys contain more than one distinct `sum_click` value.
- 8,459,320 unique student-resource-day keys exist.

Therefore we will not use subset-based duplicate deletion. Exact duplicates are removed as redundant source rows; repeated keys are handled by an explicit application grain.

### Final `Interaction` grain

For the Django application, one `Interaction` record represents:

> one student + one course presentation + one VLE resource + one day.

The business key is:

`(code_module, code_presentation, id_student, id_site, date)`

Processing is therefore:

1. Keep the raw OULAD file unchanged.
2. Remove only exact duplicate rows.
3. Group by the five fields above.
4. Sum `sum_click` within each group.
5. Store the result as `total_clicks` in the processed interaction data.

This is **aggregation, not duplicate deletion**. If the source contains, for example, 4, 1 and 8 clicks for the same student/resource/day, the processed value is 13 total clicks for that day.

On the provided dataset:

- 9,868,110 rows remain after exact de-duplication.
- 8,459,320 processed interaction rows remain after aggregation.
- This is a 20.61% reduction from the raw row count and a 14.28% reduction from the exact-deduplicated row count.

The aggregation does not discard finer timestamps because `studentVle` already records interactions at day level. Raw data remains available for audit and future analysis.

## Domain validation

- `studentAssessment.score` must be in [0, 100]. No invalid values were found.
- `assessments.weight` must be in [0, 100]. No invalid values were found.
- `studentVle.sum_click` is a non-negative count. No negative values were found.
- After aggregation, `total_clicks` remains non-negative; the minimum observed value is 1.

A passed validation rule is retained as a regression check; there is nothing to “fix” when the source already satisfies the rule.

## Modelling / leakage rule

`studentInfo.final_result` is an outcome, not an early-warning feature. Predictive features must only use information available at the intended prediction time. Future assessments, interactions, or registration information must not leak into earlier prediction windows.

## Reproducible preparation

The processing logic is kept in `scripts/prepare_interactions.py`. It reads `studentVle.csv` from the raw OULAD ZIP, removes only exact duplicates, aggregates the agreed student-resource-day grain, and writes the processed interaction table. Source and processed row counts are reported so the transformation can be audited.

## Next decision

Phase 2 is complete. Phase 3 will translate the validated OULAD structure and the agreed Interaction grain into the four core Django entities: `Etudiant`, `Cours`, `Evaluation`, and `Interaction`, without adding unnecessary models.
