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

The original `studentVle.csv` contains more than 10 million rows. Processing preserves the raw archive and uses a documented grain rather than loading every raw row as a Django ORM object by default.

## 3. Django domain model

The application uses five models.

### Student

Represents the anonymized person identified by `id_student`. Person-level characteristics include gender, region, highest education, IMD band, and disability where present in the source. The audit found 72 students whose `age_band` varies across enrolments, so age band belongs on `Enrollment`, not as an assumed permanent student attribute.

### Course

Represents one module presentation, with `code_module`, `code_presentation`, and `module_presentation_length`. The module/presentation pair is unique.

### Enrollment

Represents one student's enrolment in one module presentation. It connects `Student` to `Course` and stores enrolment-specific fields such as `age_band`, `num_of_prev_attempts`, `studied_credits`, `final_result`, `date_registration`, and `date_unregistration`. The pair `(student, course)` is unique.

This model is important because the same person may take multiple module presentations. Assessment and interaction records link to the appropriate enrolment, not only to the student identity.

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
              +----> Early-withdrawal risk indicators (Phase 7)
              |
              v
Dashboard and evidence-grounded queryable agent (later work)
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

The Django models, migrations, and controlled import were implemented and validated locally. The import validation recorded 22 courses, 28,785 students, 32,593 enrolments, 173,912 assessment records, and 8,459,320 interactions. These are audit results for the current local dataset; rerun validation if source data or transformations change.

## 6. Data-quality and missing-value policy

The guiding rule is **preserve → investigate → document → handle at point of use**.

- Missing assessment scores are missing, not zero.
- Missing registration dates are not a reliable withdrawal indicator.
- The audit found 1,111 missing `imd_band` values, 45 missing registration dates, 22,521 missing unregistration dates, 11 missing assessment definition dates (all exams), and 173 missing assessment scores (all TMA records).
- The 11 missing assessment dates should remain missing rather than be invented.
- A missing score must not silently become zero, failure, or a late-submission penalty.
- Use nullable database fields where missing numeric/date values must be represented as SQL `NULL`; distinguish database nullability from form validation.
- For model-based work, fit imputers and encoders on training data only, after defining the prediction task.

Detailed findings, cross-tabulations, decisions, and remaining audit checks are documented in [Data Quality Decisions](data-quality.md). The source audit does not establish that all missingness mechanisms are MCAR, MAR, or MNAR.

## 7. REST API and analytics

The implemented API endpoints include:

- `/api/courses/`
- `/api/students/`
- `/api/enrollments/`
- `/api/assessments/`
- `/api/analytics/engagement-by-course/`
- `/api/analytics/success-rate-by-course/`

The API uses pagination and selected filters. Large interaction tables are queried through aggregated analytical endpoints rather than exposed as millions of raw records.

### Success rate

The implemented definition is:

`success rate = (Pass + Distinction) / (Pass + Distinction + Fail) × 100`

Withdrawals are reported separately and excluded from the completed-outcome denominator. Unexpected or missing outcome categories should be reported explicitly rather than assuming that known outcome counts reconcile automatically with all enrolments.

### Engagement

The engagement-by-course endpoint reports aggregated measures such as total clicks, distinct active students, and interaction-record counts. Phase 6 added course-level engagement and success analytics, descriptive engagement/outcome analysis, course variation analysis, aggregate CSV reports, and automated tests.

The Phase 6 checkpoint passed `python backend/manage.py check` and `python backend/manage.py test analytics` (5 tests). API aggregates were also reconciled against the database: 22 course groups, 38,343,063 clicks, and 8,459,320 interaction records matched.

Engagement/outcome relationships are descriptive. Correlation does not establish causation. Registration-window duration is not a measure of actual VLE exposure.

## 8. Phase 7 — early-withdrawal risk indicators

The next development phase defines transparent early-withdrawal indicators using a stated observation cutoff. The initial design uses a day-27 cutoff and must include only information available by the end of that day.

The primary task is to distinguish students who withdraw after the cutoff from students who remain enrolled beyond it, among students who are still registered at the cutoff. Students already withdrawn on or before the cutoff are not part of the active-at-cutoff prediction cohort. Missing unregistration dates for records marked Withdrawn do not provide a known withdrawal time and must be handled explicitly rather than silently assigned a label.

Candidate features from the early interaction window include total clicks, active days, distinct resources, interaction-record count, and indicators for no recorded early activity. Define the observation window carefully against registration day and the earliest available VLE day. Do not use full-course totals, final outcomes, future interactions, or post-cutoff assessment information as predictors.

Before modelling, validate cohort construction, target prevalence, missing event-time handling, and feature availability. Establish an interpretable baseline before trying more complex models. Split data by student where a student can contribute multiple enrolments, and report class-sensitive metrics, calibration, and limitations. These are design decisions to validate in Phase 7, not completed model results.

## 9. Queryable agent and dashboard

The planned agent should answer scoped questions such as “Which students in course X show signs of disengagement, and since when?” Responses must be grounded in interaction records or validated derived indicators. Where possible, return the observation window, last recorded activity day, change in activity, and the rule that triggered the flag.

The agent must not invent causes, claim certainty, or make decisions about students. Keep it read-only for the MVP. Build the dashboard and agent only after the underlying analytics and risk rules are tested.

## 10. Privacy and repository practices

- Keep original data under `data/raw/` locally and exclude it from Git by default.
- Keep generated outputs under `data/processed/` and commit only small, non-sensitive, permitted artifacts.
- Never commit `.env`, credentials, or secrets.
- Use synthetic or suitably anonymized fixtures in tests.
- Document dataset attribution and licence in the final report.
- Use feature branches and pull requests to keep `main` reviewable.

