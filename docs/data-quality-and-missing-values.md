# Data Quality and Missing-Value Policy

**Project:** OULAD student engagement and success analytics  
**Status:** Targeted missing-data checks completed; database-import validation remains open. Update only when a documented check or source justifies a change.

## 1. Purpose and governing rule

We preserve the source data and distinguish a missing value from a real zero, a negative value that has meaning in the source, or a category such as `Unknown`.

> Do not impute or replace a missing value merely to make a table complete. First establish what the field represents, investigate the missingness pattern, and decide what the analysis requires.

The dataset documentation describes a convention in which `date_unregistration` is empty for many students who completed a course, while withdrawals are commonly identified through `final_result`. Our audit of this exact archive found exceptions, so the convention must not be used as a rule for classifying every row.

## 2. Audit findings and handling decisions

Counts below come from our audit of the downloaded OULAD archive, not from an assumption that every missing value is an error.

| Source file / column | Missing cells | Decision and findings |
|---|---:|---|
| `studentInfo.imd_band` | 1,111 | Preserve as missing. Do not invent a deprivation band. Summarize missingness by relevant groups before using this variable. |
| `studentRegistration.date_registration` | 45 | Preserve as missing. These rows include different final outcomes, so a missing registration date is not a reliable indicator of withdrawal. Do not invent an offset. |
| `studentRegistration.date_unregistration` | 22,521 | Preserve as missing; do not replace with zero or `"Unknown"`. See the outcome cross-tab below: the source convention has exceptions in this archive. |
| `assessments.date` | 11 | All 11 missing dates belong to Exam assessments. The archive contains 24 exams in total; CMA and TMA assessment dates were not missing in this audit. Preserve the unknown dates. |
| `studentAssessment.score` | 173 | All 173 missing scores are TMA records. All have a `date_submitted` value; 172 have `is_banked = 0` and one has `is_banked = 1`. A missing score is not a score of zero. |
| `vle.week_from` | 5,243 | Preserve as missing planned start-week metadata. Summarize missingness by relevant groups before use. |
| `vle.week_to` | 5,243 | Preserve as missing planned end-week metadata. Summarize missingness by relevant groups before use. |

The interaction dataset produced from `studentVle.csv` had no missing values in its six output columns after the documented deduplication and aggregation. That does not change the handling decisions for the other source tables.

### 2.1 Enrollment and registration consistency

The full enrollment key is `(code_module, code_presentation, id_student)`.

- All **32,593** rows in `studentInfo` matched one-to-one with `studentRegistration` on this key.
- There were no unmatched rows on either side of that join.
- The audit found 72 students whose `age_band` varied across enrolments. This supports keeping `age_band` at the enrollment-record grain rather than assuming it is a permanent student-level attribute. No variation was observed across enrolments for `gender`, `region`, `highest_education`, `imd_band`, or `disability` in this check.

The cross-tabulation of `date_unregistration` against `final_result` showed:

| `date_unregistration` status | Distinction | Fail | Pass | Withdrawn | Total |
|---|---:|---:|---:|---:|---:|
| Date recorded | 0 | 9 | 0 | 10,063 | 10,072 |
| Date missing | 3,024 | 7,043 | 12,361 | 93 | 22,521 |

This shows that the convention is useful but not exception-free: **9 Fail records have a date recorded**, and **93 Withdrawn records have no date recorded**. Do not infer or overwrite `final_result` from the date field alone. The 45 missing `date_registration` values also occur across more than one final outcome, so they must not be treated as a withdrawal flag.

Registration dates are relative day offsets. Negative offsets can be valid in this dataset and must not automatically be classified as errors.

### 2.2 Missing assessment scores and timing

Of the 173 missing `studentAssessment.score` values, all were TMA records. Comparing `date_submitted` with the recorded `assessments.date` for TMA records with both dates available gave:

| Submission timing relative to recorded assessment date | Records | Missing scores | Missing-score rate |
|---|---:|---:|---:|
| On or before date | 82,106 | 39 | 0.05% |
| After date | 16,320 | 134 | 0.82% |

The missing-score rate was approximately **17.3 times higher** among records submitted after the recorded assessment date. The absolute rates are still low. This is an **association, not evidence of causation**. The recorded `date` is the assessment date in the dataset; this comparison does not establish that it is a verified official deadline or explain why any score is missing.

For score-based metrics, state which records are eligible and report the denominator. Do not silently turn missing scores into zero, failure, or a late-submission penalty.

## 3. Representation in code and Django

- **Raw source:** keep the downloaded archive unchanged. Do not overwrite source CSVs.
- **pandas:** detect missingness with `isna()` / `notna()`; don't rely on equality checks against `NaN`. Keep missing values missing unless a transformation has a documented reason.
- **Django database:** use `null=True` for optional non-string fields such as dates and numeric values when missing values must be represented as SQL `NULL`. Remember that `null` controls database storage, while `blank` controls validation. For optional strings, follow Django's convention of using an empty string rather than creating two missing states (`NULL` and `""`) unless a specific schema constraint requires otherwise.
- **API/dashboard:** display an understandable label such as “Not provided” or “Unavailable” when appropriate, without writing that label back into numeric/date fields.
- **Metrics:** define eligibility and denominators explicitly. Missing scores must not silently become zero; missing values must not be counted as failures or withdrawals without a valid definition.
- **Machine learning (if included):** decide imputation/encoding inside the training pipeline after defining the prediction task. Fit preprocessing on training data only to avoid leakage. Compare methods where missingness could materially affect results and document assumptions.

## 4. Remaining checks

- [x] Cross-tab `studentRegistration.date_unregistration` missingness against `studentInfo.final_result` using the full enrollment key; document exceptions.
- [x] Check consistency of `studentInfo` and `studentRegistration` on the full enrollment key.
- [x] Inspect the 45 missing `date_registration` values against final outcomes; do not treat a blank as a withdrawal indicator.
- [x] Inspect the 173 missing `studentAssessment.score` records by assessment type, submission-date availability, and `is_banked`; compare missingness by timing against the recorded assessment date.
- [x] Inspect the 11 missing `assessments.date` records by assessment type.
- [ ] Summarize `imd_band`, `week_from`, and `week_to` missingness by relevant course/presentation or categories before using these variables in comparisons.
- [ ] Record the chosen rule next to every metric/model that is affected by missing values.
- [ ] Validate database import counts, null counts, keys and relationships against the audited source tables after the Django models and import process are implemented.

These checks describe patterns and possible inconsistencies; they do not, by themselves, prove that data are Missing Completely At Random (MCAR), Missing At Random (MAR), or Missing Not At Random (MNAR). We should not claim one of these mechanisms without a defensible analysis and assumptions.

## 5. Why we are not filling every blank with `"Unknown"`

`"Unknown"` is a string, not a universal missing-value strategy. In a numeric or date column it can break type consistency; in a categorical variable it may be useful for a specific model or display, but it still changes how that category is represented and interpreted. A display label is not the same as the stored value.

The default policy is therefore **preserve → investigate → document → handle at point of use**.

## 6. References

1. Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2017). *Open University Learning Analytics dataset*. Scientific Data, 4, 170171. https://doi.org/10.1038/sdata.2017.171 — dataset structure and conventions, including the meaning of empty unregistration dates.
2. Open University, OU Analyse. *Open University Learning Analytics dataset*. https://research.stem.open.ac.uk/ouanalyse/dataset/ — official dataset overview and access point.
3. pandas documentation. *Working with missing data*. https://pandas.pydata.org/docs/user_guide/missing_data.html — missing-value representations and `isna()` / `notna()`.
4. Django 5.2 documentation. *Model field reference*. https://docs.djangoproject.com/en/5.2/ref/models/fields/ — distinction between `null` and `blank`.
5. Hughes, R. A., Heron, J., Sterne, J. A. C., & Tilling, K. (2023). *Assumptions and analysis planning in studies with missing data in multiple variables: moving beyond the MCAR/MAR/MNAR classification*. International Journal of Epidemiology, 52(4), 1268–1275. https://doi.org/10.1093/ije/dyac234 — explains why missing-data assumptions and method choice require substantive reasoning.

---
This document records the checks completed so far. It does not claim that every missingness mechanism has been identified. Database import validation and the remaining grouped-missingness summaries are still open.
