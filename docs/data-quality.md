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

## `studentVle.csv` duplicates

`DataFrame.drop_duplicates()` compares all columns by default. Therefore rows with different `sum_click` are not exact duplicates. `drop_duplicates(subset=[...])` would impose a business key and can discard observations.

Audit of the provided raw file:

- 10,655,280 rows.
- 787,170 rows are repeated exact rows beyond their first occurrence (`df.duplicated().sum()`).
- 9,868,110 rows remain after exact de-duplication.
- 1,614,505 student-resource-day keys occur more than once.
- 1,179,074 repeated keys contain more than one distinct `sum_click` value.
- 8,459,320 unique student-resource-day keys exist.

Therefore we will not use subset-based duplicate deletion. Exact duplicates are candidates for removal; repeated keys require an explicit aggregation/grain decision for the Django `Interaction` model.

## Domain validation

- `studentAssessment.score` must be in [0, 100]. No invalid values were found.
- `assessments.weight` must be in [0, 100]. No invalid values were found.
- `studentVle.sum_click` is a non-negative count. No negative values were found.

A passed validation rule is retained as a regression check; there is nothing to “fix” when the source already satisfies the rule.

## Modelling / leakage rule

`studentInfo.final_result` is an outcome, not an early-warning feature. Predictive features must only use information available at the intended prediction time. Future assessments, interactions, or registration information must not leak into earlier prediction windows.

## Next decision

Before bulk import, define the exact grain of `Interaction` and build a reproducible preparation/import process with source-vs-processed row-count checks.
