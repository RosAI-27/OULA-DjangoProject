# OULA — Initial Architecture

## 1. Purpose

OULA is a student-success analytics project. Its first objective is to establish a reliable, explainable data foundation for exploring the relationship between student characteristics, course enrolment, assessment outcomes, and learning interactions.

The architecture is intentionally incremental. It should support the academic requirements first and avoid introducing infrastructure that the project does not yet need.

## 2. Proposed layers

```text
Source files (raw)
       |
       v
Data inspection and validation
       |
       v
Reproducible preparation scripts
       |
       v
Django domain models and database
       |
       +----> Django admin / internal inspection
       |
       +----> REST API (after core models work)
                    |
                    v
             Analytics / indicators
                    |
                    v
             Dashboard or interface
```

Predictive modelling is a later, optional stage. It must be justified by the target definition, sample size, data quality, and a leakage-safe evaluation strategy.

## 3. Domain model boundary

The four required core entities are:

- **Etudiant**: a student record.
- **Cours**: a course or module record.
- **Evaluation**: an assessment result associated with a student and a course.
- **Interaction**: an observed interaction between a student and course/resource.

Likely relationships to validate against the lecturer's specification and the source dataset:

- One student can have multiple evaluations.
- One course can have multiple evaluations.
- One student can have multiple interactions.
- One course can have multiple interactions.

Do not finalize field names, nullability, uniqueness rules, or relationship cardinality until the assignment specification and dataset schema have been checked. If an interaction refers to a specific resource, model that only if the source data supports it.

## 4. Separation of responsibilities

- `data/raw/`: original input data. Do not edit source files in place.
- `data/processed/`: generated outputs from documented preparation steps.
- `notebooks/`: exploration, charts, and experiments; not the only place where reusable transformation logic lives.
- `backend/`: Django project, domain apps, API, configuration, and application tests.
- `docs/`: architecture, data dictionary, assumptions, and decisions.
- `tests/`: cross-component or repository-level checks where useful.

For transformations that must be rerun, prefer version-controlled Python modules or scripts over relying exclusively on notebook execution order.

## 5. Data flow and integrity

1. Inspect columns, types, grain, identifiers, duplicates, missingness, and target/outcome definitions.
2. Write a data dictionary and record assumptions.
3. Prepare data with reproducible scripts and validation checks.
4. Load validated records into Django using an explicit import command or script.
5. Compare imported counts and key constraints with the source.
6. Create analytics only after the underlying data is trustworthy.

## 6. API and analytics

Django REST Framework is a planned dependency, not the first milestone. Introduce endpoints only after the models, migrations, and basic tests are stable.

Begin analytics with descriptive summaries and clear definitions. If an early-warning score is developed, document exactly what it measures and when its inputs are available. Do not present an association as causation or a risk indicator as a definitive judgement about a student.

## 7. Privacy and repository hygiene

- Never commit passwords, API keys, private environment files, or sensitive individual-level student data.
- Keep large or restricted raw datasets out of Git unless licensing and course requirements explicitly permit distribution.
- Use synthetic or anonymized examples in tests and documentation.
- Document dataset licence, provenance, and restrictions before publishing derived data.

## 8. Collaboration

- Keep `main` reviewable.
- Use focused branches for features and documentation.
- Open a pull request for review before merging substantial changes.
- Make small commits with descriptive messages.
- Ensure setup and tests are reproducible on Windows.

## 9. Decisions still open

- Exact dataset and its licence.
- Exact fields and cardinalities from the professor's specification.
- Supported Python version and dependency versions.
- Whether SQLite is sufficient for the academic prototype or another database is required.
- Prediction target and prediction time horizon, if modelling is approved.
- Dashboard technology and deployment target.
