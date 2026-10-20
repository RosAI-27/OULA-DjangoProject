# OULA — Student Success Analytics

OULA is a student-success analytics project built with Django using the Open University Learning Analytics Dataset (OULAD). The goal is to organize student enrolment, course presentation, assessment, and learning-interaction data so we can study engagement and academic outcomes, then consider transparent early-warning indicators.

## Project status

**Stage:** Architecture and repository setup. The Django application and database models have not yet been implemented.

The four assignment concepts use English model names: `Student`, `Course`, `AssessmentResult`, and `StudentInteraction`. We will also use `Enrollment` as a fifth model because a student can enrol in multiple module presentations and enrolment-specific fields belong to that relationship.

## Dataset

Source: [Kaggle — Open University Learning Analytics Dataset](https://www.kaggle.com/datasets/rocki37/open-university-learning-analytics-dataset)

OULAD contains seven related CSV files: `studentInfo.csv`, `studentRegistration.csv`, `courses.csv`, `assessments.csv`, `studentAssessment.csv`, `vle.csv`, and `studentVle.csv`.

A key modelling detail: `Course` means a **module presentation**, identified by the pair `code_module` + `code_presentation`. A student may be enrolled in multiple module presentations. The interaction table `studentVle.csv` contains roughly 10.6 million rows, so it must be inspected and processed carefully rather than blindly loaded into Django ORM objects.

See [the architecture](docs/architecture.md) and [the initial data dictionary](docs/data-dictionary.md) for the proposed mapping and validation plan.

## Core domain models

- `Student` — the anonymised person identified by `id_student`, with stable person-level characteristics.
- `Course` — a module presentation from `courses.csv`, uniquely identified by `code_module` + `code_presentation`.
- `Enrollment` — one student's enrolment in one course presentation; stores enrolment-specific details and final outcome from `studentInfo.csv` and registration dates from `studentRegistration.csv`.
- `AssessmentResult` — a student's assessment result from `studentAssessment.csv`, linked to assessment metadata in `assessments.csv` and the relevant `Enrollment`.
- `StudentInteraction` — daily student clicks on a VLE resource from `studentVle.csv`, linked to the relevant `Enrollment`.

Exact fields, constraints, and relationships must be checked against the professor's assignment sheet and the downloaded archive before migrations are created. The source-data grain and missing-value audit are documented in the architecture and data-quality notes.

## Required MVP

The professor's brief requires:

- **Django models:** `Student`, `Course`, `Enrollment`, `AssessmentResult`, `StudentInteraction`.
- **DRF API and dashboard:** pass rate by course, engagement/results relationship, and at-risk student segments.
- **Agentic component:** answer questions about possible disengagement, including when warning signs appeared, with justification grounded in interaction data.

Risk indicators must be explainable and uncertain, not treated as definitive judgments. “No recorded interaction” is not automatically proof of disengagement. See [architecture and interpretation rules](docs/architecture.md#assignment-mvp-and-interpretation-rules).

## Planned workflow

1. Inspect and document the seven source tables.
2. Validate data quality, keys, and relationships.
3. Prepare data with reproducible Python scripts while preserving the raw files.
4. Implement the four core Django models, migrations, admin registration, and tests.
5. Import validated data and compare imported counts with source counts.
6. Add descriptive analytics; introduce a REST API once the core backend is stable.
7. Evaluate whether predictive modelling is justified by the target definition and leakage-safe validation.
8. Add a dashboard or intelligent-agent interface only after the underlying outputs are reliable.

## Planned repository layout

```text
OULA-DjangoProject/
├── backend/                 # Django project and domain app
├── data/
│   ├── raw/                 # Original files; excluded from Git by default
│   └── processed/           # Generated outputs; excluded by default
├── notebooks/               # Exploratory analysis and experiments
├── docs/                    # Architecture, data dictionary, decisions
├── tests/                   # Automated tests
├── .env.example             # Safe environment-variable template
├── .gitignore
├── requirements.txt
└── README.md
```

This is the target layout, not a claim that every component is implemented yet. Work will proceed in small, reviewable steps.

## Development environment

Development is planned on Windows with Visual Studio Code. Confirm the installed Python version before creating the virtual environment and installing dependencies.

## Data, privacy, and modelling principles

- Do not commit secrets, local environment files, or raw/sensitive student-level data.
- Keep raw source files unchanged.
- Avoid target leakage: predictive features must only use information available at the intended prediction time.
- Establish a simple baseline before complex models.
- Report limitations and use metrics appropriate to the prediction task; accuracy alone is insufficient.

## Collaboration

Use feature branches and pull requests for substantial changes. Keep `main` reviewable so a classmate and the professor can follow progress.
