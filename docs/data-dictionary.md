# OULAD Source Data Dictionary (Initial)

This is a starting reference based on the published OULAD schema. Confirm all columns and row counts against the exact archive downloaded from the project's Kaggle source before coding or reporting results.

## English domain model mapping

Use the following names consistently in Django code, API responses, tests, and project documentation:

| Domain model | Meaning | Main source |
|---|---|---|
| `Student` | A person identified by `id_student` | `studentInfo.csv` (validate repeated characteristics across enrolments) |
| `CoursePresentation` | One module offering identified by `code_module` + `code_presentation` | `courses.csv` |
| `Enrollment` | One student's registration in one course presentation | `studentInfo.csv`, `studentRegistration.csv` |
| `AssessmentResult` | One student's submission/result for an assessment | `studentAssessment.csv`, joined with `assessments.csv` |
| `Interaction` | A student's recorded clicks on a VLE resource on a relative day | `studentVle.csv`, enriched with `vle.csv` |

`Enrollment` is an additional proposed model, not a replacement for the four assignment concepts. Confirm this extension against the assignment sheet before migrations are created.

## Identifier conventions

| Field | Meaning | Notes |
|---|---|---|
| `code_module` | Module identifier | Not unique across presentations by itself |
| `code_presentation` | Module presentation/run | Pair with `code_module` |
| `id_student` | Anonymised student identifier | One student may have several module enrolments |
| `id_assessment` | Assessment identifier | Join assessment definitions to submissions |
| `id_site` | VLE resource identifier | Identifies learning material in VLE metadata |

## Source files

### `studentInfo.csv`

Common documented columns: `code_module`, `code_presentation`, `id_student`, `gender`, `region`, `highest_education`, `imd_band`, `age_band`, `num_of_prev_attempts`, `studied_credits`, `disability`, `final_result`.

Grain: one student-module-presentation record. `final_result` contains the recorded final outcome (commonly Pass, Fail, Distinction, or Withdrawn). This outcome should not be used as an input feature when predicting that same outcome.

### `studentRegistration.csv`

Common documented columns: `code_module`, `code_presentation`, `id_student`, `date_registration`, `date_unregistration`.

Grain: registration record for a student in a module presentation. Dates are numeric offsets relative to the module presentation timeline, not calendar dates.

### `courses.csv`

Common documented columns: `code_module`, `code_presentation`, `module_presentation_length`.

Grain: one module presentation. The natural matching key is `(code_module, code_presentation)`.

### `assessments.csv`

Common documented columns: `code_module`, `code_presentation`, `id_assessment`, `assessment_type`, `date`, `weight`.

Grain: one assessment definition. The assessment date is generally an offset in days from the module presentation start.

### `studentAssessment.csv`

Common documented columns: `id_assessment`, `id_student`, `date_submitted`, `is_banked`, `score`.

Grain: one recorded student assessment submission/result. Not every student has a row for every assessment. Scores are typically on a 0–100 scale; missing scores must be investigated, not automatically imputed.

### `vle.csv`

Common documented columns: `id_site`, `code_module`, `code_presentation`, `activity_type`, `week_from`, `week_to`.

Grain: one VLE resource within a module presentation. Resource identifiers and metadata should be validated before joining.

### `studentVle.csv`

Common documented columns: `code_module`, `code_presentation`, `id_student`, `id_site`, `date`, `sum_click`.

Grain: a student's clicks on a resource on a day. The published dataset contains approximately 10.6 million rows. Treat it as a large event table; use chunked processing or documented aggregation for exploratory analytics and avoid naive ORM bulk insertion.

## Join plan to validate

- `studentInfo` ↔ `studentRegistration`: `code_module`, `code_presentation`, `id_student`
- `studentInfo` ↔ `studentAssessment`: use `id_student` together with assessment/module-presentation context; do not join by student ID alone if that would mix enrolments
- `studentAssessment` ↔ `assessments`: `id_assessment`
- `studentInfo` ↔ `courses`: `code_module`, `code_presentation`
- `studentVle` ↔ `vle`: `id_site` plus module/presentation context where applicable
- `studentVle` ↔ `studentInfo`: `id_student`, `code_module`, `code_presentation`

## Validation checklist

- [ ] Verify exact file names and columns from the archive.
- [ ] Compare source row counts with expected documented counts.
- [ ] Check uniqueness at each table's true grain.
- [ ] Check missingness and sentinel values (for example, `-1` date offsets if present).
- [ ] Check orphaned foreign keys before loading.
- [ ] Document how withdrawn students and missing assessment scores are represented.
- [ ] Keep raw files unchanged and excluded from Git.
