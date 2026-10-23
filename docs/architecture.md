# OULA — System Architecture

## 1. Project overview

OULA is a student-success analytics project built with Django and the Open University Learning Analytics Dataset (OULAD). Its purpose is to help a teaching team explore student engagement and academic outcomes, then investigate transparent early-warning indicators.

The implementation is incremental: reliable data, clear metric definitions, tested API outputs, and explainable indicators come before a dashboard or agent interface. Predictive modelling is optional and must be justified by a clearly defined target and leakage-safe validation.

## 2. Dataset and relational grain

OULAD is distributed as seven related CSV files:

- `studentInfo.csv`: student characteristics and final outcome per module presentation.
- `studentRegistration.csv`: registration and unregistration day offsets.
- `courses.csv`: module-presentation metadata.
- `assessments.csv`: assessment definitions, dates, types, and weights.
- `studentAssessment.csv`: student assessment submissions and scores.
- `vle.csv`: virtual learning environment resource metadata.
- `studentVle.csv`: student clicks on resources by day.

Important identifiers include `code_module`, `code_presentation`, `id_student`, `id_assessment`, and `id_site`.

A course is a **module presentation**, uniquely identified by the pair `(code_module, code_presentation)`, not by `code_module` alone. A student may enrol in multiple module presentations. OULAD date fields are relative day offsets on a presentation timeline, not calendar dates; negative offsets can be valid.

The original `studentVle.csv` contains more than 10 million rows. Processing must preserve the raw archive and use a documented grain rather than loading every raw row as a Django ORM object by default.

## 3. Django domain model

The application uses five models.

### Student

Represents the anonymized person identified by `id_student`. Person-level characteristics include gender, region, highest education, IMD band, and disability where present in the source. The audit found 72 students whose `age_band` varies across enrolments, so age band belongs on `Enrollment`, not as an assumed permanent student attribute.

### Course

Represents one module presentation, with `code_module`, `code_presentation`, and `module_presentation_length`. The module/presentation pair is unique.

### Enrollment

Represents one student's enrolment in one module presentation. It connects `Student` to `Course` and stores enrolment-specific fields such as `age_band`, `num_of_prev_attempts`, `studied_credits`, `final_result`, `date_registration`, and `date_unregistration`. The pair `(student, course)` is unique.

This model is important because the same person may take multiple module presentations. Assessment and interaction records must link to the appropriate enrolment, not only to the student identity.

### Assessment

Represents a student's assessment record linked to an enrolment, including assessment identifier, type, assessment date, weight, submission date, banking status, and score. Assessment definitions originate in `assessments.csv`; student submissions and scores originate in `studentAssessment.csv`. The assessment must belong to the same module presentation as the enrolment. Not every student necessarily has a submission for every assessment.

### Interaction

Represents aggregated VLE activity at the grain:

**one enrolment + one VLE resource + one relative day.**

The source fields include module, presentation, student, resource (`id_site`), relative day (`date`), and clicks (`sum_click`). Repeated observations at the agreed grain are aggregated by summing clicks. The unique key is `(enrollment, id_site, date)`.

## 4. Architecture and data flow

```text
OULAD raw CSV archive (read-only)
              |
              v
Inspection, data dictionary, quality audit
              |
              v
Reproducible preparation and validation scripts
              |
              v
Prepared/aggregated data + count/key reconciliation
              |
              v
Django models and controlled database import
              |
              +----> Django admin and model checks
              |
              v
Django REST Framework API
              |
              v
Validated descriptive analytics
              |
              +----> Student-risk indicators
              |
              v
Dashboard and evidence-grounded queryable agent
```

Notebooks are appropriate for exploration and documented experiments. Reusable transformations should live in scripts or Python modules so the workflow can be rerun consistently.

## 5. Data preparation and import validation

The interaction preparation process:

1. Reads the raw archive without modifying it.
2. Removes exact duplicate source rows.
3. Aggregates repeated observations at the enrolment-resource-day grain by summing click counts.
4. Writes prepared data to `data/processed/`, which is excluded from version control.
5. Validates row counts, keys, and click totals.

For the downloaded archive, `studentVle.csv` contained 10,655,280 source rows. Removing 787,170 exact duplicate rows left 9,868,110 rows before aggregation into 8,459,320 interaction records. The database total clicks reconciled with the prepared CSV total: 38,343,063.

The Django models, migrations, and controlled import have been implemented and validated locally. The import validation recorded 22 courses, 28,785 students, 32,593 enrolments, 173,912 assessment records, and 8,459,320 interactions. These are audit results for the current local dataset; rerun validation if source data or transformations change.

## 6. Data-quality and missing-value policy

The guiding rule is **preserve → investigate → document → handle at point of use**.

- Missing assessment scores are missing, not zero.
- Missing registration dates are not a reliable withdrawal indicator.
- The audit found 1,111 missing `imd_band` values, 45 missing registration dates, 22,521 missing unregistration dates, 11 missing assessment definition dates (all exams), and 173 missing assessment scores (all TMA records).
- The 11 missing assessment dates should remain missing rather than be invented.
- A missing score must not silently become zero, failure, or a late-submission penalty.
- Use nullable database fields where missing numeric/date values must be represented as SQL `NULL`; distinguish database nullability from form validation.
- For model-based work, fit imputers and encoders on training data only, after defining the prediction task.

Detailed findings, cross-tabulations, decisions, and remaining audit checks are documented in [Data Quality and Missing-Value Policy](data-quality-and-missing-values.md). The source audit does not establish that all missingness mechanisms are MCAR, MAR, or MNAR.

## 7. REST API and analytics

The core API endpoints currently implemented locally are:

- `/api/courses/`
- `/api/students/`
- `/api/enrollments/`
- `/api/assessments/`
- `/api/analytics/engagement-by-course/`
- `/api/analytics/success-rate-by-course/`

The API uses pagination and selected filters. Large interaction tables should be queried through aggregated analytical endpoints rather than exposed as millions of raw records.

### Success rate

The initial definition is:

`success rate = (Pass + Distinction) / (Pass + Distinction + Fail) × 100`

Withdrawals are reported separately and excluded from the completed-outcome denominator. The API should also be checked for unexpected or missing outcome categories so the total enrollment count and known outcome counts are not assumed to reconcile automatically.

### Engagement

The engagement-by-course endpoint reports aggregated measures such as total clicks, distinct active students, and interaction-record counts. Next, validate the aggregation and complete the engagement/results relationship analysis at the student-enrolment level. Start with descriptive summaries and correlation; correlation does not establish causation.

Before moving on, add automated tests for endpoint responses, metric denominators, filters, empty groups, missing/unexpected outcomes, and relevant edge cases. A successful server check alone does not prove the analytics are correct.

## 8. Student-risk indicators

The first risk-segmentation approach should be transparent and rule-based rather than automatically introducing a predictive model. Potential indicators include low recent activity relative to the course timeline, a substantial decline in activity, or weak/missing assessment evidence. The exact rules and observation windows must be defined and tested before being treated as project results.

- Use only information available by the stated observation day.
- Do not use final outcomes as early-warning features when those outcomes would not yet be known.
- Distinguish no recorded activity from confirmed disengagement.
- Show the evidence window, rule, and coverage for each flagged enrolment.
- Treat risk as uncertain and suitable for human follow-up, not as a definitive judgement about a student.

If prediction is later justified, define the target and prediction horizon first, establish a simple baseline, choose a split that reflects the intended generalization setting, and prevent target leakage. Report class-wise metrics and limitations rather than accuracy alone.

## 9. Queryable agent and dashboard

The planned agent should answer scoped questions such as “Which students in course X show signs of disengagement, and since when?” Responses must be grounded in interaction records or validated derived indicators. Where possible, return the observation window, last recorded activity day, change in activity, and the rule that triggered the flag.

The agent must not invent causes, claim certainty, or make decisions about students. Keep it read-only for the MVP. Build the dashboard and agent only after the underlying analytics and risk rules are tested.

## 10. Privacy, repository practices, and next steps

- Keep original data under `data/raw/` locally and exclude it from Git by default.
- Keep generated outputs under `data/processed/` and commit only small, non-sensitive, permitted artifacts.
- Never commit `.env`, credentials, or secrets.
- Use synthetic or suitably anonymized fixtures in tests.
- Document dataset attribution and licence in the final report.
- Use feature branches and pull requests to keep `main` reviewable.

### Current implementation status

- **Completed:** architecture, targeted source-data audit, interaction preparation, Django models/migrations, controlled import, and source/database count reconciliation.
- **Implemented locally; needs stronger validation:** core DRF endpoints and initial course-level engagement and success-rate analytics.
- **Next:** add automated API and metric tests; complete engagement/results analysis; validate edge cases and outcome categories.
- **After that:** implement transparent risk segmentation, then the evidence-grounded agent and dashboard.

This document distinguishes work implemented locally from work not yet completed. Update the status as code is validated and synchronized.
