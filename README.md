# OULA — Student Success Analytics

OULA is a student-success analytics project built with Django. The goal is to organize student, course, assessment, and learning-interaction data so that we can explore academic engagement and performance, then develop transparent early-warning indicators before considering predictive models.

## Project status

**Stage:** Architecture and repository setup.

The repository is being structured before implementation. Existing course requirements and the professor's four core models take priority over speculative features.

## Core domain models

- `Etudiant` — student information, including registration date and withdrawal status where available.
- `Cours` — course/module information (for example, a course code such as `AAA-2013J`).
- `Evaluation` — an assessment linked to a student and a course, with a score and submission date where supported by the source data.
- `Interaction` — a student's interaction with a course resource, including resource identifier, date, and activity type/count where supported by the source data.

Exact fields and relationships will be confirmed against the course specification and the dataset before implementation.

## Planned workflow

1. Inspect and document the source data.
2. Validate data quality and prepare reproducible transformations.
3. Model the core entities in Django and persist validated records.
4. Expose selected data through Django REST Framework when the core backend is stable.
5. Build descriptive analytics and transparent risk indicators.
6. Evaluate whether predictive modelling is justified by the available data and validation design.
7. Add a dashboard or intelligent-agent interface only after the underlying outputs are reliable.

## Planned repository layout

```text
OULA-DjangoProject/
├── backend/                 # Django project and domain apps
├── data/
│   ├── raw/                 # Original datasets; usually excluded from Git
│   └── processed/           # Reproducible cleaned outputs; usually excluded from Git
├── notebooks/               # Exploratory analysis and experiments
├── docs/                    # Architecture, data dictionary, and decisions
├── tests/                   # Project-level tests
├── .env.example             # Names of required environment variables, no secrets
├── .gitignore
├── requirements.txt
└── README.md
```

This is the target layout, not a claim that all components are implemented yet. We will introduce the Django project files in small, verifiable steps.

## Development environment

Development is planned on Windows with Visual Studio Code. Setup instructions will be added once the Django and dependency versions are selected.

## Data, privacy, and modelling principles

- Do not commit secrets, local environment files, or sensitive student-level data.
- Keep raw data separate from processed data.
- Avoid target leakage: features used to predict a future outcome must only use information available before that outcome.
- Establish a simple baseline before testing complex models.
- Report limitations and use metrics appropriate to the prediction task; do not treat accuracy as the only measure of quality.

## Collaboration

Use feature branches and pull requests for substantial changes. Keep `main` in a reviewable state so classmates and the professor can follow progress.
