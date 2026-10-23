# OULA — Student Success Analytics

OULA is a Django-based student-success analytics project using the Open University Learning Analytics Dataset (OULAD). It organizes student enrolments, course presentations, assessment results, and VLE interactions so we can study engagement and academic outcomes and build explainable early-warning indicators.

## Project status

**Current implementation checkpoint:** data-quality audit and reproducible interaction preparation are complete; the Django models, migrations, controlled OULAD import, and core DRF list/engagement endpoints have been implemented and manually exercised. Automated tests and the remaining course analytics are still in progress.

The application uses five Django models: `Student`, `Course`, `Enrollment`, `Assessment`, and `Interaction`. `Enrollment` represents a student's participation in one module presentation and keeps enrolment-level information separate from person-level attributes. See [the architecture and implementation decisions](docs/architecture.md) for model grain, data-quality decisions, API scope, metric definitions, limitations, and next steps.

## Dataset

Source: [Kaggle — Open University Learning Analytics Dataset](https://www.kaggle.com/datasets/rocki37/open-university-learning-analytics-dataset)

OULAD contains seven related CSV files: `studentInfo.csv`, `studentRegistration.csv`, `courses.csv`, `assessments.csv`, `studentAssessment.csv`, `vle.csv`, and `studentVle.csv`.

A course offering is a **module presentation**, identified by the pair `code_module` + `code_presentation`. The same student may be enrolled in multiple presentations. The raw `studentVle.csv` contains over 10 million rows, so the project prepares and aggregates it reproducibly instead of naively inserting every raw row into Django.

## Current backend endpoints

- `/api/courses/`
- `/api/students/`
- `/api/enrollments/`
- `/api/assessments/`
- `/api/analytics/engagement-by-course/`

The engagement endpoint aggregates interactions by module presentation. It does not expose millions of raw interaction rows. Automated tests for endpoint behavior and analytics correctness remain a required quality gate.

## Required MVP

The course brief calls for:
- Django models for student, course, assessment, and interaction concepts.
- A DRF API and dashboard for course pass rate, engagement/results relationship, and at-risk segments.
- An agentic component that answers questions about possible disengagement and when warning signs appeared, with justification grounded in interaction data.

Risk indicators must be explainable and uncertain, not treated as definitive judgments. “No recorded interaction” is not proof of disengagement. Predictive modelling is optional unless justified and must avoid target leakage.

## Workflow and next steps

1. Add automated model/API/import validation tests.
2. Implement the course-presentation success-rate endpoint with an explicit denominator and separately reported withdrawals.
3. Analyse engagement at the student-enrolment level and compare it with assessment/final outcomes.
4. Define and validate transparent at-risk segments.
5. Build the dashboard on stable API outputs.
6. Add the evidence-grounded, read-only query agent.
7. Finish reproducibility instructions, evaluation, and limitations.

The detailed implementation status and technical decisions are maintained in [docs/architecture.md](docs/architecture.md).

## Repository layout

```text
OULA-DjangoProject/
├── backend/                 # Django project and analytics app
├── data/
│   ├── raw/                 # Original archive; excluded from Git
│   └── processed/           # Generated data; excluded from Git
├── scripts/                 # Reproducible preparation and audit scripts
├── docs/                    # Architecture, data dictionary, decisions
├── notebooks/               # Exploratory analysis and experiments
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
