# OULA — Architecture and Implementation Decisions

## 1. Purpose

OULA is a Django-based student-success analytics application using the Open University Learning Analytics Dataset (OULAD). It is intended to help a teaching team explore student engagement and academic outcomes, identify explainable early-warning signals, and query the evidence behind those signals.

The course MVP is:
1. Pass/success rate by module presentation.
2. Relationship between engagement and results.
3. Transparent at-risk segments.
4. A REST API and dashboard.
5. A read-only, evidence-grounded query agent after the analytics are reliable.

Prediction is not a prerequisite. If predictive modelling is added, it must use a defined prediction time, leakage-safe features, a simple baseline, appropriate evaluation metrics, and clearly stated limitations.

**Branch status matters:** the Django implementation described in this document is present in the current development work, but the backend code is not yet committed to `main` as of this revision. The main-branch README and this architecture should not be interpreted as proof that these endpoints can already be run from `main`.

## 2. Source data and grain

The project uses the seven related OULAD CSV files: `studentInfo.csv`, `studentRegistration.csv`, `courses.csv`, `assessments.csv`, `studentAssessment.csv`, `vle.csv`, and `studentVle.csv`.

Important identifiers:
- `code_module`: module code.
- `code_presentation`: a particular presentation/run of a module.
- `id_student`: anonymised person identifier.
- `id_assessment`: assessment identifier.
- `id_site`: VLE resource identifier.

A course offering is a **module presentation**, uniquely matched by `(code_module, code_presentation)`, not by `code_module` alone. The same person may have multiple enrolments, and enrolment-level fields such as age band, prior attempts, credits, final result, and registration dates belong to the student–presentation relationship.

OULAD's dates are day offsets on a module-presentation timeline, not calendar dates.

## 3. Domain model in the development implementation

The professor's four required concepts are represented with consistent English Django names. The implementation has five database models because a separate `Enrollment` is needed to represent the source data's actual grain.

| Assignment concept / purpose | Django model | Grain and responsibility |
|---|---|---|
| Student (`Etudiant`) | `Student` | One anonymised person, identified by unique `id_student`; stable person-level characteristics only. |
| Course (`Cours`) | `Course` | One module presentation, identified by unique `code_module` + `code_presentation`. |
| Enrolment relationship | `Enrollment` | One student in one module presentation; stores enrolment-specific attributes and final outcome. |
| Assessment (`Evaluation`) | `Assessment` | One student's recorded result/submission for an assessment, linked to an `Enrollment`. |
| Interaction (`Interaction`) | `Interaction` | Aggregated daily clicks for one enrolment and one VLE resource. |

### Student

Fields include `id_student`, `gender`, `region`, `highest_education`, `imd_band`, and `disability`. The source audit found students whose `age_band` differs across enrolments, so `age_band` is stored on `Enrollment`, not as a permanent person attribute.

### Course

Fields: `code_module`, `code_presentation`, and `module_presentation_length`. A database uniqueness constraint protects the natural key `(code_module, code_presentation)`.

### Enrollment

Foreign keys to `Student` and `Course`; fields include `age_band`, `num_of_prev_attempts`, `studied_credits`, `final_result`, `date_registration`, and `date_unregistration`. The pair `(student, course)` is unique. Registration values remain relative day offsets; missing values are preserved.

### Assessment

Each row belongs to an `Enrollment` and carries `id_assessment`, `assessment_type`, `assessment_date`, `weight`, `date_submitted`, `is_banked`, and nullable `score`. The pair `(enrollment, id_assessment)` is unique.

**Current design trade-off:** assessment definition metadata from `assessments.csv` is stored alongside each student's assessment result rather than in a separate assessment-definition model. This avoids adding a sixth model to the current MVP and matches the current import/API shape, but repeats metadata across students. It also means the database uniqueness constraint alone does not ensure that an `id_assessment` belongs to the same module presentation as the enrolment. Add importer validation and automated tests for this cross-table rule. If richer assessment-level queries or database-level enforcement become important, consider a separate assessment-definition model; that change would require coordinated migration, importer, serializer, and API updates.

A missing score is not equivalent to zero, and the absence of a submission row is not automatically a zero score.

### Interaction

Each row belongs to an `Enrollment` and contains `id_site`, `date`, and `total_clicks`. Its grain is:

`one enrollment + one VLE resource + one day`

The raw `studentVle.csv` contains repeated observations at this grain, so exact duplicate source rows are removed and repeated observations are aggregated by summing `sum_click`. The uniqueness constraint is `(enrollment, id_site, date)`. Resource metadata from `vle.csv` is not currently a separate database model.

## 4. Data preparation, import, and integrity

The raw archive is read-only and remains outside version control. Preparation scripts create reproducible processed data; the development importer loads validated records in batches. The raw ZIP and generated interaction CSV must not be committed to Git.

Recorded local preparation/import checkpoint:
- Raw `studentVle` source rows: 10,655,280.
- Exact duplicate source rows removed: 787,170.
- Rows after exact de-duplication: 9,868,110.
- Aggregated interaction rows: 8,459,320.
- Imported courses: 22.
- Imported students: 28,785.
- Imported enrolments: 32,593.
- Imported assessment results: 173,912.
- Imported interactions: 8,459,320.
- Imported total clicks: 38,343,063; matches the processed CSV total.

These are recorded development-run checks, not results reproducible from `main` alone until the backend implementation is merged. Matching row counts and click totals do **not** prove row-by-row parity. Re-run validation after changing preparation or import logic.

Other known data-quality decisions:
- `imd_band` is missing for 1,111 source records; preserve missingness.
- 11 assessment definitions have missing assessment dates; these are exams in the audited archive.
- 173 student-assessment rows have missing scores; do not fill these with zero by default.
- 72 students have `age_band` values that vary across enrolments; keep this field on `Enrollment`.

## 5. Backend and API in development

The development implementation includes these REST endpoints:
- `/api/courses/`
- `/api/students/`
- `/api/enrollments/`
- `/api/assessments/`
- `/api/analytics/engagement-by-course/`

The list endpoints use pagination; student, enrolment, and assessment endpoints expose relevant filters. The engagement endpoint returns grouped summaries by module presentation, including total clicks, distinct active students, and interaction-record count. It aggregates in the database rather than returning millions of raw interaction rows.

The endpoints have been manually exercised in the development workspace. Automated API/model tests remain a quality gate; an earlier `manage.py test analytics` run found zero tests. Before calling the API complete, add tests for filters, pagination, empty/null cases, aggregation correctness, foreign-key integrity, and the assessment-to-enrolment course-consistency rule. The backend code must be merged before these endpoints are available from `main`.

## 6. Analytics definitions and safeguards

### Success rate by module presentation

Define the numerator and denominator explicitly:
- Numerator: enrolments with `final_result` equal to `Pass` or `Distinction`.
- Denominator: enrolments with a completed, non-withdrawn final outcome.
- Report withdrawals separately rather than hiding them in the denominator.

This is a proposed MVP definition; confirm it against the professor's rubric before treating it as final. Use the same definition in API responses, charts, and the report.

### Engagement and outcomes

Aggregate clicks at the student-enrolment level before comparing engagement with scores or final outcomes. Start with descriptive summaries and appropriate association measures. Correlation does not establish that engagement causes academic success.

### At-risk segments and agent

Begin with transparent rules, documented time windows, and evidence such as recent activity changes and available assessment performance. Do not use final results or future activity as predictors for an earlier warning date. “No recorded interaction” is not proof of disengagement.

The eventual query agent should be read-only and explain the course presentation, observation window, criteria, and evidence behind each answer. It must not invent causes or make decisions about students.

## 7. Project workflow and next work

Completed in the current development work (not yet all committed to `main`):
1. Repository and environment setup.
2. OULAD audit and reproducible interaction preparation.
3. Five Django models and migrations.
4. Controlled import and count/click-total validation.
5. Core DRF list endpoints and course-engagement aggregation.

Next:
1. Add automated tests for models, imports/validation, filters, pagination, and API aggregations.
2. Implement the course-presentation success-rate endpoint with the denominator above, after confirming the rubric definition.
3. Implement student-enrolment-level engagement/outcome analysis.
4. Define and test explainable risk segments.
5. Build the dashboard on stable API outputs.
6. Add the evidence-grounded read-only query agent.
7. Merge the backend in a reviewed, reproducible state and complete documentation, evaluation, and limitations.

The phase numbers are a project work plan, not an official professor-defined sequence. The professor's deliverables remain the acceptance criteria.

## 8. Repository and privacy practices

- Keep raw files under `data/raw/` locally and exclude them from Git.
- Exclude large generated datasets under `data/processed/` unless a small permitted artifact is specifically needed.
- Never commit `.env`, credentials, or secrets.
- Use synthetic or suitably anonymised fixtures in automated tests.
- Document dataset provenance, attribution, and licence in the final report.
- Use feature branches and pull requests for reviewable changes; avoid overwriting local work or force-pushing to synchronize branches.
