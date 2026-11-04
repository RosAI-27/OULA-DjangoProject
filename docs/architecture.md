# OULA — System Architecture

## 1. Project overview

OULA is a student-success analytics project built with Django and the Open University Learning Analytics Dataset (OULAD). Its purpose is to help a teaching team explore student engagement and academic outcomes, then investigate transparent early-warning indicators.

The implementation was delivered in stages: source-data inspection and preparation, a relational Django backend, descriptive analytics, a REST API, a rule-based risk indicator, an interactive dashboard, and a conversational agent. The current risk indicator is a transparent heuristic, not a trained predictive model.

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
              +----> Rule-based early-withdrawal risk indicator
              |                  |
              v                  v
         Dashboard <------ Retrospective validation
              |
              v
       Conversational agent
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

At the Phase 6 checkpoint, `python backend/manage.py check` and `python backend/manage.py test analytics` passed (5 tests). API aggregates were also reconciled against the database: 22 course groups, 38,343,063 clicks, and 8,459,320 interaction records matched. Later phases added dashboard and risk-indicator tests; run the current test suite to verify the integrated version.

Engagement/outcome relationships are descriptive. Correlation does not establish causation. Registration-window duration is not a measure of actual VLE exposure.

## 8. Phase 7 — early-withdrawal risk indicators

The application implements an additive rule-based score at a selected course-day cutoff (day 60 by default). It uses VLE clicks and assessment scores recorded up to the cutoff. The final outcome is returned only for retrospective comparison and is not used to calculate the score.

The rules assign points for no recorded clicks, activity below a course-level lower-quartile threshold, no recorded activity in the preceding 14 days, no non-missing assessment score by the cutoff, and low or moderate mean assessment scores. Risk levels are high (60 or more), medium (30–59), and low (below 30).

The score is not capped at 100; the listed rules can produce a total of up to 140. It must not be interpreted as a probability or percentage. The current cohort query excludes enrollments unregistered by the cutoff, but does not fully enforce that registration dates are present and on or before the cutoff. This remains a methodological limitation.

A retrospective comparison is implemented for module AAA, presentation 2013J, at day 60. It covers 361 enrollments. The observed Fail-or-Withdrawn proportions were 85.7% in the high-risk group (7 enrollments), 64.3% in the medium-risk group (28), 18.1% in the low-risk group (326), and 23.0% overall. This single-course, single-cutoff comparison is descriptive and is not sufficient to establish general predictive performance.

## 9. Dashboard and conversational agent

The dashboard is served at `/dashboard/` and uses Django templates and Chart.js. It displays overall enrollment and outcome indicators, success and withdrawal rates by module, weekly engagement, engagement by final outcome, risk scores and explanations, and a retrospective validation summary.

The LangChain agent uses three tools that call the project's REST API: success and withdrawal statistics by course, weekly engagement, and students flagged by the risk indicator. It is instructed to ground project figures in tool responses, ask for missing module or presentation context, explain risk reasons, and avoid treating scores as verdicts. It uses a configured Gemini model with fallback models.

The agent requires a Google AI Studio API key and a running Django server. Its API base URL is configurable through `API_BASE_URL`. The dashboard loads Chart.js from a CDN.

## 10. Privacy and repository practices

- Keep original data under `data/raw/` locally and exclude it from Git by default.
- Keep generated outputs under `data/processed/` and commit only small, non-sensitive, permitted artifacts.
- Never commit `.env`, credentials, or secrets.
- Use synthetic or suitably anonymized fixtures in tests.
- Document dataset attribution and licence in the final report.
- Use feature branches and pull requests to keep `main` reviewable.

