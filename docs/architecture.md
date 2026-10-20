# OULA — Architecture for the Open University Learning Analytics Dataset

## 1. Purpose

OULA is a student-success analytics project built with Django. The first goal is a reliable, explainable foundation for exploring student enrolment, assessment performance, and engagement with the Virtual Learning Environment (VLE).

We will satisfy the course requirements first and keep the system incremental. Predictive modelling and an intelligent-agent interface are later options, not prerequisites for a good project.

## 2. Source dataset and relational grain

The project uses the Open University Learning Analytics Dataset (OULAD), obtained through the Kaggle dataset link shared for this project. OULAD is distributed as seven related CSV tables. The commonly documented release contains about 32,593 student-module-presentation records and 10.6 million daily student-resource interaction records.

The key identifiers are:

- `code_module`: module code.
- `code_presentation`: a particular presentation/run of a module.
- `id_student`: anonymised student identifier.
- `id_assessment`: assessment identifier.
- `id_site`: VLE resource identifier.

**Important modelling detail:** a course/module is not uniquely identified by `code_module` alone. Use the pair `(code_module, code_presentation)` as the natural identifier for a module presentation.

The data describes student enrolments in module presentations, not just one demographic row per person. The same student can appear in multiple module presentations.

## 3. Required core Django models

The four assignment concepts use English Django model names: `Student`, `Course`, `AssessmentResult`, and `StudentInteraction`. We will also add `Enrollment` as a fifth model because the dataset's natural grain is a student enrolled in a particular module presentation. `Enrollment` connects `Student` and `Course` and stores attributes/outcomes that belong to that specific enrolment. Confirm the final naming against the assignment sheet before migrations.

### Student

Represents the anonymised person identified by `id_student`. Keep person-level characteristics here only when the source supports treating them as stable across enrolments, such as `gender`, `region`, `highest_education`, `imd_band`, and `disability`. The source audit found 72 students whose `age_band` varies across enrolments, so do not store `age_band` as a permanent Student attribute.

### Course

Represents a **module presentation**. Candidate fields:
- `code_module`
- `code_presentation`
- `module_presentation_length`

Use the composite natural key `(code_module, code_presentation)` for matching the source data. Django may use its normal surrogate primary key while enforcing a unique constraint on these two fields.

### Enrollment

Represents one student's enrolment in one module presentation, at the grain of `studentInfo.csv` joined with `studentRegistration.csv`. It links one `Student` to one `Course` and stores enrolment-specific fields: `age_band`, `num_of_prev_attempts`, `studied_credits`, `final_result`, `date_registration`, and `date_unregistration`. Enforce uniqueness on `(student, course)`. Registration dates are relative day offsets, not calendar dates; preserve missing values.

This separation matters because the same person may enrol in multiple module presentations, and some fields can vary across those enrolments. It also avoids incorrectly treating `id_student` alone as the primary key of an enrolment row.

### AssessmentResult

Represents an individual student's assessment result, joining assessment metadata in `assessments.csv` with submissions/results in `studentAssessment.csv`. Assessment metadata includes `id_assessment`, `assessment_type`, `date`, and `weight`; submissions include `id_assessment`, `id_student`, `date_submitted`, `is_banked`, and `score`. Link each result to the appropriate `Enrollment`, and validate that the assessment belongs to the same module presentation as the enrolment. Do not assume every student submitted every assessment. Missing submissions and missing scores need explicit treatment.

### StudentInteraction

Represents a student's interaction with a VLE resource on a particular day. `studentVle.csv` contains `code_module`, `code_presentation`, `id_student`, `id_site`, `date`, and `sum_click`. Link it to `Enrollment`, and preserve the grain `(enrollment, id_site, date)` after aggregation.

Resource metadata in `vle.csv` includes `id_site`, module/presentation identifiers, `activity_type`, `week_from`, and `week_to`.

**Scale warning:** `studentVle.csv` has roughly 10.6 million rows. Do not blindly load the entire file into Django ORM objects or commit it to Git. First inspect memory/disk needs and the academic requirements; use chunked processing and/or aggregated interaction features where appropriate. Keep raw files outside version control unless permission and licensing clearly allow distribution.

## 4. Seven source CSVs and their roles

| CSV | Role | Core model / use |
|---|---|---|
| `studentInfo.csv` | Student characteristics and final outcome per module presentation | Student + Enrollment |
| `studentRegistration.csv` | Registration and unregistration dates | Enrich Enrollment / validation |
| `courses.csv` | Module presentation metadata | Course |
| `assessments.csv` | Assessment definitions, dates, types and weights | Enrich AssessmentResult |
| `studentAssessment.csv` | Student submissions and scores | AssessmentResult |
| `vle.csv` | VLE resource metadata | Enrich Interaction |
| `studentVle.csv` | Daily student-resource clicks | StudentInteraction / interaction aggregation |

These seven source tables do not mean we must create seven Django models. We keep the four assignment concepts (`Student`, `Course`, `AssessmentResult`, `StudentInteraction`) and add `Enrollment` because it represents a necessary relationship/grain in the source data. This is a justified fifth model, not a one-model-per-CSV design.

## 5. Proposed layers

```text
Seven original CSV files (read-only)
          |
          v
Inspection + data dictionary + quality checks
          |
          v
Reproducible Python preparation scripts
          |
          v
Validated import / aggregation
          |
          v
Django models: Student, Course, Enrollment, AssessmentResult, StudentInteraction
          |
          +----> Django admin and model tests
          |
          +----> REST API (after core models are stable)
                         |
                         v
                Descriptive analytics
                         |
                         v
                Dashboard / interface
```

Notebooks are for exploration and documented experiments. Reusable transformations should gradually move into scripts or Python modules so they can be rerun consistently.

## 6. Data preparation and integrity workflow

1. Record the downloaded archive's provenance, licence, and file list.
2. Inspect each CSV's columns, data types, row count, missingness, duplicates, identifier uniqueness, and row grain.
3. Document join keys and test referential integrity.
4. Keep raw source files unchanged.
5. Write repeatable cleaning/validation scripts; never silently drop records just because values are missing.
6. Decide how to represent dates, missing scores, withdrawn students, and students with no recorded VLE activity.
7. Import manageable, validated tables into Django and compare record counts and keys against the source.
8. For `studentVle.csv`, process in chunks or aggregate by a clearly documented grain rather than loading all rows as individual ORM objects by default.

## 7. Analytics and modelling safeguards

Begin with descriptive analysis and clearly defined indicators. If prediction is later justified:

- define the outcome and prediction time horizon first;
- prevent target leakage, especially from `final_result` or activity occurring after the intended prediction date;
- split data in a way that reflects the intended generalisation setting;
- compare with a simple baseline;
- report class-wise metrics and limitations, not accuracy alone;
- interpret risk indicators as uncertain signals, not definitive judgements about individual students.

## 8. Assignment MVP and interpretation rules

The professor's required MVP is:

1. **Pass rate by course:** define the denominator explicitly. A sensible first definition is students with a final outcome of Pass or Distinction divided by students with a completed, non-withdrawn outcome; report the withdrawal rate separately so excluding withdrawals does not hide them.
2. **Engagement/results relationship:** aggregate `sum_click` at the student-enrolment level, then compare engagement indicators with assessment scores and/or final outcomes. Start with descriptive summaries and correlation; correlation does not establish that engagement causes success.
3. **At-risk segments:** begin with transparent, documented rules or descriptive segments (for example, low recent activity relative to the course timeline, alongside weak or missing assessment results). Show the criteria and coverage, and do not label a student as certainly dropping out.
4. **DRF API and dashboard:** expose tested, aggregated outputs from the backend before building dashboard charts.

### Agentic component (after the analytics are trustworthy)

The agent should answer scoped questions such as: “Which students in course X show signs of disengagement, and since when?” Its response must be grounded in queryable interaction records or derived indicators and explain the evidence (for example, last recorded activity day and a change in weekly click totals).

- Treat `studentVle.date` and assessment dates as day offsets on the module-presentation timeline, not calendar dates.
- Distinguish “no recorded interaction” from “confirmed disengagement”; activity data alone may be incomplete.
- Use only information available up to the stated observation date when describing early-warning signals.
- Return the criteria, evidence window, and relevant dates with the answer. The agent must not invent causes or claim certainty.
- Keep the agent read-only for the MVP; it should not make decisions about students or modify records.
## 9. Repository and privacy practices

- Keep original data under `data/raw/` locally, but excluded from Git by default.
- Keep generated outputs under `data/processed/`, and commit only small, non-sensitive, permitted artifacts.
- Never commit `.env`, credentials, or secrets.
- Use synthetic or suitably anonymised fixtures in tests.
- Document dataset attribution and licence in the final project report.
- Keep `main` reviewable and collaborate using feature branches and pull requests.

## 10. Next implementation milestone

With the professor's brief now confirmed, inspect the actual downloaded archive and validate the proposed model fields/relationships against it. Then implement:
1. data inspection report and data dictionary;
2. reproducible preparation/validation scripts;
3. Django project and app;
4. five domain models (`Student`, `Course`, `Enrollment`, `AssessmentResult`, `StudentInteraction`), migrations, admin registration, and tests;
5. a controlled import command.

The architecture is based on the documented OULAD tables; exact nullability, constraints, and import strategy must be validated against the downloaded files and the assignment sheet.
