# Data Quality and Missing-Value Policy

**Project:** OULAD student engagement and success analytics  
**Status:** Initial policy for implementation; update only when a documented check or source justifies a change.

## 1. Purpose and governing rule

We preserve the source data and distinguish a missing value from a real zero, a negative value that has meaning in the source, or a category such as `Unknown`.

> Do not impute or replace a missing value merely to make a table complete. First establish what the field represents, investigate the missingness pattern, and decide what the analysis requires.

A missing value can mean different things in different fields. The dataset documentation says that `date_unregistration` is empty for students who completed a course, while students who unregistered have `final_result = Withdrawal`. That documented convention is useful evidence, but we must reconcile the missing dates with `final_result` in our exact archive rather than infer each record's meaning from the blank alone. See the official OULAD data descriptor and dataset page in References.

## 2. Audit findings and handling decisions

Counts below come from our audit of the downloaded OULAD archive, not from an assumption that every missing value is an error.

| Source file / column | Missing cells | Decision for now | Follow-up / analytical caution |
|---|---:|---|---|
| `studentInfo.imd_band` | 1,111 | Preserve as missing in source and database. Do not invent a deprivation band. | Report missingness when comparing this variable; consider a labelled missing category only for a specific analysis/model if justified. |
| `studentRegistration.date_registration` | 45 | Preserve as missing; do not invent a registration offset. | Inspect these rows and cross-check enrollment keys and related fields. |
| `studentRegistration.date_unregistration` | 22,521 | Preserve as missing. Do not replace with zero or the string `"Unknown"`. | Official OULAD documentation says completed students have this field empty and withdrawals are identified in `studentInfo.final_result`. Cross-tab missingness against `final_result` before deriving an interpretation or a withdrawal indicator. |
| `assessments.date` | 11 | Preserve as missing; do not invent an assessment due date. | Inspect assessment type, module and presentation. Do not assume all missing dates share one explanation. |
| `studentAssessment.score` | 173 | Preserve as missing; do not replace with zero. | Inspect affected assessments and records. A missing score is not evidence of a score of zero; exclude from score-based calculations unless a justified method says otherwise, and report the denominator. |
| `vle.week_from` | 5,243 | Preserve as missing. | Treat as unavailable planned start-week metadata unless the source gives a stronger interpretation. |
| `vle.week_to` | 5,243 | Preserve as missing. | Treat as unavailable planned end-week metadata unless the source gives a stronger interpretation. |

The interaction dataset produced from `studentVle.csv` had no missing values in its six output columns after the documented deduplication and aggregation. That does not change the handling decisions for the other source tables.

## 3. Representation in code and Django

- **Raw source:** keep the downloaded archive unchanged. Do not overwrite source CSVs.
- **pandas:** detect missingness with `isna()` / `notna()`; don't rely on equality checks against `NaN`. Keep missing values missing unless a transformation has a documented reason.
- **Django database:** use `null=True` for optional non-string fields such as dates and numeric values when missing values must be represented as SQL `NULL`. Remember that `null` controls database storage, while `blank` controls validation. For optional strings, follow Django's convention of using an empty string rather than creating two missing states (`NULL` and `""`) unless a specific schema constraint requires otherwise.
- **API/dashboard:** display an understandable label such as “Not provided” or “Unavailable” when appropriate, without writing that label back into numeric/date fields.
- **Metrics:** define eligibility and denominators explicitly. Missing scores must not silently become zero; missing values must not be counted as failures or withdrawals without a valid definition.
- **Machine learning (if included):** decide imputation/encoding inside the training pipeline after defining the prediction task. Fit preprocessing on training data only to avoid leakage. Compare methods where missingness could materially affect results and document assumptions.

## 4. Checks required before declaring the missing-data review closed

- [ ] Cross-tab `studentRegistration.date_unregistration` missingness against `studentInfo.final_result` using the full enrollment key (`code_module`, `code_presentation`, `id_student`); investigate any unexpected combinations.
- [ ] Inspect the 45 missing `date_registration` rows and check whether related enrollment data are otherwise consistent.
- [ ] Inspect the 173 missing `studentAssessment.score` rows by assessment type, module/presentation, and other available fields; do not infer the missingness mechanism from counts alone.
- [ ] Inspect the 11 missing `assessments.date` records by assessment type and module/presentation.
- [ ] Summarize `imd_band`, `week_from`, and `week_to` missingness by relevant course/presentation or categories before using these variables in comparisons.
- [ ] Record the chosen rule next to every metric/model that is affected by missing values.
- [ ] Validate database import counts, null counts, keys and relationships against the audited source tables.

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
This document records our current policy; it does not claim that every missingness mechanism has already been identified. Update it when the targeted checks above provide evidence.
