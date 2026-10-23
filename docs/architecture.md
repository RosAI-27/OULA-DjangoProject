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

**Important modelling detail:** a course offering is not uniquely identified by `code_module` alone. Use the pair `(code_module, code_presentation)` as the natural identifier for a `CoursePresentation`.

The data describes student enrolments in course presentations, not just one demographic row per person. The same student can appear in multiple course presentations.

## 3. Consistent English domain names

Use English names consistently in Python code, Django models, APIs, tests, and documentation.

| Previous French name | English name | Intended meaning |
|---|---|---|
| `Etudiant` | `Student` | A person identified by OULAD's `id_student`. |
| `Cours` | `CoursePresentation` | One module offering, identified by `code_module` + `code_presentation`. |
| `Evaluation` | `AssessmentResult` | A student's submission/result joined to the relevant assessment metadata. |
| `Interaction` | `Interaction` | A student's recorded interaction with a VLE resource. |
| `Inscription` | `Enrollment` | A student's registration in one course presentation. |

### Why add `Enrollment`?

A `Student` is a person; an `Enrollment` is that person's participation in one particular course presentation. OULAD's `studentInfo.csv` is at student-module-presentation grain, and fields such as `final_result`, `num_of_prev_attempts`, `studied_credits`, and registration dates relate to an enrolment rather than to a person in general.

Keeping these concepts separate avoids using `id_student` as if it uniquely identified every student-course record. Proposed relationship:

```text
Student 1 ─── many Enrollment many ─── 1 CoursePresentation
                     |
                     ├── AssessmentResult
                     └── Interaction
```

We will implement `Enrollment` as the fifth domain model alongside the four core concepts. This preserves the distinction between a person and their participation in a specific course presentation.

## 4. Proposed core models and source mapping

### Student

Represents a person identified by `id_student`.

Candidate identifier:
- `id_student`

Student characteristics in `studentInfo.csv` include `gender`, `region`, `highest_education`, `imd_band`, `age_band`, and `disability`. Because the source file is at enrolment grain, validate that these attributes are consistent across a person's enrolments before storing them once on `Student`. If they are not consistent, document a justified alternative rather than silently choosing a value.

### CoursePresentation

Represents one module presentation. Candidate fields:
- `code_module`
- `code_presentation`
- `module_presentation_length`

Enforce uniqueness on `(code_module, code_presentation)`. Django may use a surrogate primary key while preserving this natural-key constraint.

### Enrollment

Represents one student's registration in one course presentation. It links `Student` and `CoursePresentation` and should be unique for that pair unless source validation demonstrates a different grain.

Candidate enrolment-level fields from `studentInfo.csv` and `studentRegistration.csv`:
- `num_of_prev_attempts`
- `studied_credits`
- `final_result`
- `date_registration`
- `date_unregistration`

Registration and assessment dates are offsets relative to the module-presentation timeline, not calendar dates. Validate missing values and sentinel values before selecting field types and nullability.

### AssessmentResult

Represents a student's submission/result for an assessment. It draws from `studentAssessment.csv` and the matching assessment definition in `assessments.csv`.

Submission/result fields include:
- `id_assessment`
- `date_submitted`
- `is_banked`
- `score`

Assessment metadata includes `assessment_type`, `date`, and `weight`. Resolve the relevant module presentation through assessment metadata, and link the result to the correct enrolment. Do not join only on `id_student` or assume every student submitted every assessment. Missing submissions and missing scores need explicit treatment.

Whether assessment definitions should become a separate lookup model is an implementation decision to make after validating the assignment scope and source keys; avoid duplicating metadata without documenting the trade-off.

### Interaction

Represents a student's interaction with a VLE resource on a particular day. `studentVle.csv` contains `code_module`, `code_presentation`, `id_student`, `id_site`, `date`, and `sum_click`.

Resource metadata in `vle.csv` includes `id_site`, module/presentation identifiers, `activity_type`, `week_from`, and `week_to`. Link an interaction to the correct enrolment and validate resource keys before importing.

**Scale warning:** `studentVle.csv` has roughly 10.6 million rows. Do not blindly load the entire file into Django ORM objects or commit it to Git. First inspect memory/disk needs and the academic requirements; use chunked processing and/or aggregated interaction features where appropriate. Keep raw files outside version control unless permission and licensing clearly allow distribution.

## 5. Seven source CSVs and their roles

| CSV | Role | Primary model / use |
|---|---|---|
| `studentInfo.csv` | Student characteristics and final outcome per course presentation | Student + Enrollment |
| `studentRegistration.csv` | Registration and unregistration dates | Enrollment |
| `courses.csv` | Course presentation metadata | CoursePresentation |
| `assessments.csv` | Assessment definitions, dates, types and weights | AssessmentResult metadata; consider a separate lookup if justified |
| `studentAssessment.csv` | Student submissions and scores | AssessmentResult |
| `vle.csv` | VLE resource metadata | Enrich Interaction |
| `studentVle.csv` | Daily student-resource clicks | Interaction / interaction aggregation |

These seven source tables do not mean we must create seven Django models. Add a model only when it clarifies a real entity or protects data integrity, and keep the professor's required concepts visible.

## 6. Proposed layers

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
Django models: Student, CoursePresentation, Enrollment,
               AssessmentResult, Interaction
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

## 7. Data preparation and integrity workflow

1. Record the downloaded archive's provenance, licence, and file list.
2. Inspect each CSV's columns, data types, row count, missingness, duplicates, identifier uniqueness, and row grain.
3. Document join keys and test referential integrity.
4. Keep raw source files unchanged.
5. Write repeatable cleaning/validation scripts; never silently drop records just because values are missing.
6. Decide how to represent dates, missing scores, withdrawn students, and students with no recorded VLE activity.
7. Import manageable, validated tables into Django and compare record counts and keys against the source.
8. For `studentVle.csv`, process in chunks or aggregate by a clearly documented grain rather than loading all rows as individual ORM objects by default.

## 8. Analytics and modelling safeguards

Begin with descriptive analysis and clearly defined indicators. If prediction is later justified:

- define the outcome and prediction time horizon first;
- prevent target leakage, especially from `final_result` or activity occurring after the intended prediction date;
- split data in a way that reflects the intended generalisation setting;
- compare with a simple baseline;
- report class-wise metrics and limitations, not accuracy alone;
- interpret risk indicators as uncertain signals, not definitive judgements about individual students.

## 9. Assignment MVP and interpretation rules

The professor's required MVP is:

1. **Pass rate by course:** define the denominator explicitly. A sensible first definition is students with a final outcome of Pass or Distinction divided by students with a completed, non-withdrawn outcome; report the withdrawal rate separately so excluding withdrawals does not hide them.
2. **Engagement/results relationship:** aggregate `sum_click` at the student-enrolment level, then compare engagement indicators with assessment scores and/or final outcomes. Start with descriptive summaries and correlation; correlation does not establish that engagement causes success.
3. **At-risk segments:** begin with transparent, documented rules or descriptive segments (for example, low recent activity relative to the course timeline, alongside weak or missing assessment results). Show the criteria and coverage, and do not label a student as certainly dropping out.
4. **DRF API and dashboard:** expose tested, aggregated outputs from the backend before building dashboard charts.

### Agentic component (after the analytics are trustworthy)

The agent should answer scoped questions such as: “Which students in course X show signs of disengagement, and since when?” Its response must be grounded in queryable interaction records or derived indicators and explain the evidence (for example, last recorded activity day and a change in weekly click totals).

- Treat `studentVle.date` and assessment dates as day offsets on the course-presentation timeline, not calendar dates.
- Distinguish “no recorded interaction” from “confirmed disengagement”; activity data alone may be incomplete.
- Use only information available up to the stated observation date when describing early-warning signals.
- Return the criteria, evidence window, and relevant dates with the answer. The agent must not invent causes or claim certainty.
- Keep the agent read-only for the MVP; it should not make decisions about students or modify records.

## 10. Repository and privacy practices

- Keep original data under `data/raw/` locally, but excluded from Git by default.
- Keep generated outputs under `data/processed/`, and commit only small, non-sensitive, permitted artifacts.
- Never commit `.env`, credentials, or secrets.
- Use synthetic or suitably anonymised fixtures in tests.
- Document dataset attribution and licence in the final project report.
- Keep `main` reviewable and collaborate using feature branches and pull requests.

## 11. Next implementation milestone

Before writing Django models:
1. confirm the assignment sheet permits the additional `Enrollment` model;
2. inspect the actual downloaded archive and validate all proposed fields, keys, and relationships;
3. validate whether assessment metadata and student results should be separate tables;
4. write the data inspection report and reproducible validation scripts;
5. then implement the Django project and models, migrations, admin registration, tests, and controlled import command.

This architecture is a proposal based on the documented OULAD tables. Exact nullability, constraints, and import strategy must be validated against the downloaded files and assignment sheet.
