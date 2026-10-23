# OULA — Student Success Analytics

OULA is a Django-based student-success analytics project using the Open University Learning Analytics Dataset (OULAD). It organizes student enrolments, course presentations, assessment results, and VLE interactions to study engagement and academic outcomes and build explainable early-warning indicators.

## Repository status

**Important branch distinction:** the Django models, importer, and REST API described in [the architecture](docs/architecture.md) exist in the current development work, but they are **not yet present on `main`**. The current `main` branch contains the initial repository, data-preparation work, and documentation. Do not treat an endpoint or model as available from `main` until its implementation has been merged.

The intended domain model has five Django models: `Student`, `Course`, `Enrollment`, `Assessment`, and `Interaction`. `Enrollment` represents a student's participation in one module presentation and keeps enrolment-level information separate from person-level attributes. The architecture document distinguishes the intended/current development design from what is committed to `main`.

## Dataset

Source: [Kaggle — Open University Learning Analytics Dataset](https://www.kaggle.com/datasets/rocki37/open-university-learning-analytics-dataset)

OULAD contains seven related CSV files: `studentInfo.csv`, `studentRegistration.csv`, `courses.csv`, `assessments.csv`, `studentAssessment.csv`, `vle.csv`, and `studentVle.csv`.

A course offering is a **module presentation**, identified by the pair `code_module` + `code_presentation`. The same student may be enrolled in multiple presentations. The raw `studentVle.csv` contains over 10 million rows, so the project prepares and aggregates it reproducibly instead of naively inserting every raw row into Django.

## Course MVP

The professor's brief calls for:
- Django models for student, course, assessment, and interaction concepts.
- A DRF API and dashboard for course pass rate, engagement/results relationship, and at-risk segments.
- An agentic component that answers questions about possible disengagement and when warning signs appeared, with justification grounded in interaction data.

Risk indicators must be explainable and uncertain, not treated as definitive judgments. “No recorded interaction” is not proof of disengagement. Predictive modelling is optional unless justified and must avoid target leakage.

## Workflow

1. Preserve and audit the original dataset.
2. Prepare interactions at the documented student–module-presentation–resource–day grain.
3. Integrate the Django backend and automated tests through reviewed pull requests.
4. Implement the course-presentation success-rate endpoint with an explicit denominator and separately reported withdrawals.
5. Analyse engagement at the student-enrolment level and compare it with assessment/final outcomes.
6. Define and validate transparent at-risk segments.
7. Build the dashboard on stable API outputs.
8. Add the evidence-grounded, read-only query agent.
9. Finish reproducibility instructions, evaluation, and limitations.

## Repository layout

```text
OULA-DjangoProject/
├── backend/                 # Django backend (currently placeholder on main)
├── data/
│   ├── raw/                 # Original archive; excluded from Git
│   └── processed/           # Generated data; excluded from Git
├── scripts/                 # Reproducible preparation scripts
├── docs/                    # Architecture, data dictionary, data-quality decisions
├── notebooks/               # Exploratory analysis and experiments
├── tests/                   # Test guidance and, as implementation is merged, automated tests
├── .env.example             # Safe environment-variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Data, privacy, and modelling principles

- Keep raw source files unchanged and out of Git.
- Never commit `.env`, credentials, or secrets.
- Preserve missing scores as missing unless a documented analytical rule says otherwise; missing is not zero.
- Prevent target leakage: features must only use information available at the intended prediction time.
- Establish a simple baseline before complex models.
- Use metrics appropriate to the question and document limitations; accuracy alone is insufficient.

## Collaboration

Use feature branches and pull requests for substantial changes. Keep `main` reviewable so classmates and the professor can follow progress.
