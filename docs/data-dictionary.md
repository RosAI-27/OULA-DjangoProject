# OULAD Source Data Dictionary

This reference summarizes the seven CSV tables in the OULAD archive used for the project. The row counts and data-quality findings recorded in [data-quality.md](data-quality.md) come from the downloaded project archive; rerun the audit if the archive changes.

## Identifier conventions

| Field | Meaning | Notes |
|---|---|---|
| `code_module` | Module identifier | Not unique across presentations by itself |
| `code_presentation` | Module presentation/run | Pair with `code_module` |
| `id_student` | Anonymised student identifier | One student may have several module enrolments |
| `id_assessment` | Assessment identifier | Resolve assessment metadata before attaching a result to an enrolment |
| `id_site` | VLE resource identifier | Resource IDs must be interpreted with module/presentation context |

## Source files and grain

### `studentInfo.csv`

Columns: `code_module`, `code_presentation`, `id_student`, `gender`, `region`, `highest_education`, `imd_band`, `age_band`, `num_of_prev_attempts`, `studied_credits`, `disability`, `final_result`.

Grain: one student-module-presentation record. The outcome is commonly Pass, Fail, Distinction, or Withdrawn. It must not be used as a predictor for an earlier warning or for predicting that same outcome.

### `studentRegistration.csv`

Columns: `code_module`, `code_presentation`, `id_student`, `date_registration`, `date_unregistration`.

Grain: registration record for a student in a module presentation. Dates are offsets relative to the module-presentation timeline, not calendar dates. Missing registration/unregistration values must retain their meaning.

### `courses.csv`

Columns: `code_module`, `code_presentation`, `module_presentation_length`.

Grain: one module presentation. Natural matching key: `(code_module, code_presentation)`.

### `assessments.csv`

Columns: `code_module`, `code_presentation`, `id_assessment`, `assessment_type`, `date`, `weight`.

Grain: one assessment definition. Assessment dates are day offsets; 11 missing assessment dates in the audited archive were exams.

### `studentAssessment.csv`

Columns: `id_assessment`, `id_student`, `date_submitted`, `is_banked`, `score`.

Grain: one recorded student assessment submission/result. Not every student has a row for every assessment. The audit found 173 missing scores, all associated with TMA records; a missing score is not automatically zero. Scores in the audited archive were within the expected 0–100 range.

### `vle.csv`

Columns: `id_site`, `code_module`, `code_presentation`, `activity_type`, `week_from`, `week_to`.

Grain: one VLE resource within a module presentation. Validate the resource's module/presentation context when joining.

### `studentVle.csv`

Columns: `code_module`, `code_presentation`, `id_student`, `id_site`, `date`, `sum_click`.

Raw grain: student-resource-day observations within a module presentation. The audited archive has 10,655,280 rows. Preparation removes only exact duplicate rows and then aggregates by `(code_module, code_presentation, id_student, id_site, date)`, summing `sum_click` into `total_clicks`. This produces 8,459,320 interaction rows; see [data-quality.md](data-quality.md).

## Join and integrity rules

- `studentInfo` ↔ `studentRegistration`: `code_module`, `code_presentation`, `id_student`.
- `studentAssessment` ↔ `assessments`: `id_assessment`; use the assessment definition's module/presentation to verify the result belongs to the same enrolment.
- `studentInfo` ↔ `courses`: `code_module`, `code_presentation`.
- `studentVle` ↔ `vle`: match `id_site` and validate module/presentation context.
- `studentVle` ↔ `studentInfo`: `id_student`, `code_module`, `code_presentation`.

Do not join student-level results on `id_student` alone when that could mix course presentations. Preserve the distinction between a person and one enrolment in one module presentation.

## Implementation mapping

The development Django design currently maps the source into `Student`, `Course`, `Enrollment`, `Assessment`, and `Interaction`. This is a five-model design, not a one-model-per-CSV design. See [architecture.md](architecture.md) for the current design trade-off around storing assessment definition metadata on each result row.

## Remaining validation

Before treating the full import as reproducible from the repository, ensure the backend implementation is committed and automated checks cover:
- referential integrity and duplicate keys;
- consistency of assessment module/presentation with the linked enrolment;
- missing scores and withdrawn outcomes;
- source versus imported counts and click totals;
- the aggregation grain for interactions.

Raw source data remains unchanged and excluded from Git.
