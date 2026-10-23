# OULA — Student Success Analytics

OULA is a student-success analytics project built with Django and the Open University Learning Analytics Dataset (OULAD). It organizes student identities, course presentations, enrolments, assessments, and learning-platform interactions so we can study engagement and academic outcomes and develop transparent early-warning indicators.

## Project status

The data-quality audit and interaction-preparation workflow are documented. Django models and the controlled data import have been implemented and validated locally. The core REST API is implemented locally; analytics validation, automated tests, risk segmentation, the queryable agent, and dashboard remain in progress. Backend changes are being synchronized to this feature branch.

| Workstream | Status |
|---|---|
| Repository setup and architecture | Complete |
| OULAD inspection and targeted missing-value audit | Complete; a few grouped-missingness checks remain |
| Interaction preparation and source-count reconciliation | Complete |
| Django models, migrations, and data import | Implemented and validated locally |
| REST API endpoints | Core endpoints implemented locally; automated tests needed |
| Course engagement and success-rate analytics | Initial endpoints implemented; further validation needed |
| Engagement/results relationship | To complete |
| Explainable student-risk indicators | Planned |
| Evidence-grounded queryable agent | Planned |
| Dashboard | Planned |

## Dataset

OULAD contains seven related CSV files: `studentInfo.csv`, `studentRegistration.csv`, `courses.csv`, `assessments.csv`, `studentAssessment.csv`, `vle.csv`, and `studentVle.csv`.

- [Official OULAD dataset page](https://analyse.kmi.open.ac.uk/open_dataset)
- [Kaggle dataset mirror](https://www.kaggle.com/datasets/rocki37/open-university-learning-analytics-dataset)

A course in this project represents a **module presentation**, identified by `code_module` + `code_presentation`. A student may be enrolled in multiple presentations. The original `studentVle.csv` contains over 10 million rows, so it must be processed carefully rather than blindly loaded as individual ORM objects.

The original archive is kept locally under `data/raw/` and is not committed to Git. Prepared interaction data is stored under `data/processed/` and is also excluded from version control.

## Core Django models

The implementation uses five models:

- **`Student`** — anonymized person identified by `id_student`, with person-level characteristics.
- **`Course`** — one module presentation, uniquely identified by `code_module` + `code_presentation`.
- **`Enrollment`** — one student's enrolment in one course presentation; holds enrolment-specific characteristics, registration offsets, and final outcome.
- **`Assessment`** — assessment metadata and a student's submission/result linked to an enrolment.
- **`Interaction`** — aggregated clicks at the grain of one enrolment + one VLE resource + one relative day.

`Enrollment` is necessary because assessment and interaction records belong to a particular student-course presentation, not to a student identity alone. See [the architecture](docs/architecture.md), [data dictionary](docs/data-dictionary.md), and [data-quality and missing-value policy](docs/data-quality-and-missing-values.md).

## Required MVP

The project aims to deliver:

- **REST API and dashboard:** success rate by course, engagement/results relationship, and student-risk segments.
- **Explainable risk indicators:** transparent criteria and supporting evidence, not definitive claims about an individual student's intentions or future.
- **Queryable agent:** answers questions such as “Which students in course X show signs of disengagement, and since when?” with evidence from interaction data.

The initial success-rate definition is Pass + Distinction divided by completed outcomes (Pass + Distinction + Fail); withdrawals are reported separately. “No recorded interaction” is not automatically proof of disengagement. Correlation between engagement and outcomes does not establish causation.

## Data preparation and validation

The preparation script leaves the raw archive unchanged, removes exact duplicate source rows, and aggregates repeated student-resource-day observations by summing clicks. The intended interaction grain is `(enrollment, id_site, date)`.

For the downloaded archive, the audited `studentVle.csv` had 10,655,280 source rows, 787,170 exact duplicate rows were removed, and 9,868,110 rows remained before aggregation into 8,459,320 interaction records. The imported database total for clicks was reconciled with the prepared CSV total: 38,343,063.

Important missing-data decisions are recorded in [the missing-value policy](docs/data-quality-and-missing-values.md): missing scores are not zero; missing registration dates do not reliably classify withdrawal; and OULAD dates are relative day offsets, not calendar dates.

## Development workflow

1. Preserve and audit raw source data.
2. Prepare and validate tables with reproducible scripts.
3. Import data through a controlled process and compare counts, keys, and aggregates.
4. Validate API behaviour and analytics with automated tests and explicit metric definitions.
5. Build explainable risk segments using only information available at the stated observation time.
6. Add the queryable agent and dashboard after the analytical outputs are reliable.
7. Consider predictive modelling only if the target and prediction horizon are clearly defined and validation can prevent leakage.

## Repository layout

```text
OULA-DjangoProject/
├── backend/                 # Django project and analytics app
├── data/
│   ├── raw/                 # Original files; excluded from Git
│   └── processed/           # Generated outputs; excluded from Git
├── notebooks/               # Exploration and experiments
├── docs/                    # Architecture, data dictionary, decisions
├── scripts/                 # Reproducible audit and preparation scripts
├── .env.example             # Safe environment-variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Data, privacy, and modelling principles

- Do not commit secrets, local environment files, or raw student-level data.
- Keep raw source files unchanged.
- Do not turn missing values into zero or an invented category without a documented reason.
- Prevent target leakage: features must use only information available at the intended prediction time.
- Establish a simple, interpretable baseline before complex models.
- Report denominators, limitations, and metrics appropriate to the task; accuracy alone is insufficient.
- Treat risk indicators as uncertain signals that support human review, not automated decisions about students.

## Collaboration

Use feature branches and pull requests for substantial changes. Keep `main` reviewable so classmates and the professor can follow the work.
