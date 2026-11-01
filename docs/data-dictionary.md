# OULA — Data Dictionary

## 1. Purpose

This document describes the OULAD source tables, the main fields used in the project, the relationships between records, and the data preparation decisions applied before importing the data into Django.

The source dataset is the Open University Learning Analytics Dataset (OULAD).

- Official dataset: https://analyse.kmi.open.ac.uk/open_dataset
- Kaggle mirror: https://www.kaggle.com/datasets/rocki37/open-university-learning-analytics-dataset

The local source archive is `data/raw/OULA.zip`. The archive is preserved unchanged.

## 2. Source Tables

The OULAD archive contains seven CSV tables used in the current workflow.

| Source table | Purpose | Important identifiers |
|---|---|---|
| `courses.csv` | Course presentations and their lengths | `code_module`, `code_presentation` |
| `studentInfo.csv` | Student characteristics and final outcomes for each presentation | `id_student`, `code_module`, `code_presentation` |
| `studentRegistration.csv` | Registration and withdrawal information | `id_student`, `code_module`, `code_presentation` |
| `assessments.csv` | Assessment definitions and weights | `id_assessment`, `code_module`, `code_presentation` |
| `studentAssessment.csv` | Student submissions and assessment scores | `id_student`, `id_assessment` |
| `studentVle.csv` | Student interactions with virtual learning environment resources | Student, presentation, resource, and date |
| `vle.csv` | Virtual learning environment resource metadata | `id_site`, course presentation |

## 3. Important Field Definitions

### 3.1 `courses.csv`

| Field | Meaning |
|---|---|
| `code_module` | Identifier of the course module |
| `code_presentation` | Identifier of a particular presentation of the module |
| `module_presentation_length` | Length of the presentation in days |

**Record grain:** one course presentation.

The combination of `code_module` and `code_presentation` identifies a course presentation.

### 3.2 `studentInfo.csv`

| Field | Meaning |
|---|---|
| `code_module` | Course module identifier |
| `code_presentation` | Course presentation identifier |
| `id_student` | Student identifier |
| `gender` | Recorded gender category |
| `region` | Student region category |
| `highest_education` | Highest recorded education category |
| `imd_band` | Recorded Index of Multiple Deprivation band |
| `age_band` | Student age category |
| `num_of_prev_attempts` | Number of previous attempts |
| `studied_credits` | Number of credits the student is studying |
| `disability` | Recorded disability indicator |
| `final_result` | Recorded final outcome category |

**Record grain:** one student within one course presentation.

Some of these attributes describe the student, while others describe the student's participation in a particular presentation. The Django design separates student identity from enrolment-specific attributes.

### 3.3 `studentRegistration.csv`

| Field | Meaning |
|---|---|
| `code_module` | Course module identifier |
| `code_presentation` | Course presentation identifier |
| `id_student` | Student identifier |
| `date_registration` | Registration date represented as a relative day |
| `date_unregistration` | Unregistration date represented as a relative day, when available |

**Record grain:** one student within one course presentation.

A missing `date_unregistration` must not automatically be interpreted as a data error; it may indicate that no unregistration date was recorded.

### 3.4 `assessments.csv`

| Field | Meaning |
|---|---|
| `code_module` | Course module identifier |
| `code_presentation` | Course presentation identifier |
| `id_assessment` | Assessment identifier |
| `assessment_type` | Assessment type, such as TMA, CMA, or Exam |
| `date` | Assessment date represented as a relative day; may be missing |
| `weight` | Assessment contribution expressed as a percentage |

**Record grain:** one assessment definition.

Assessment dates can be missing. In the audited dataset, 11 assessment dates were missing, all associated with exams. These missing dates should remain missing unless a justified source-based correction becomes available.

### 3.5 `studentAssessment.csv`

| Field | Meaning |
|---|---|
| `id_assessment` | Assessment identifier |
| `id_student` | Student identifier |
| `date_submitted` | Submission date represented as a relative day |
| `is_banked` | Indicator of whether the result was banked |
| `score` | Recorded assessment score |

**Record grain:** one student's record for one assessment.

The audited source contained 173,912 rows, with 173 missing scores. Missing scores are not equivalent to scores of zero and must be represented as missing in the application.

The audit found no duplicate combinations of `id_student` and `id_assessment` in this table.

### 3.6 `studentVle.csv`

| Field | Meaning |
|---|---|
| `code_module` | Course module identifier |
| `code_presentation` | Course presentation identifier |
| `id_student` | Student identifier |
| `id_site` | Virtual learning environment resource identifier |
| `date` | Interaction date represented as a relative day |
| `sum_click` | Number of recorded clicks in the source observation |

**Raw record grain:** one source observation for a student, course presentation, resource, and day.

The interaction preparation process performs two operations:

1. Removes exact duplicate source rows.
2. Aggregates repeated observations for the same student, course presentation, resource, and day by summing `sum_click`.

The resulting interaction grain is one student enrolment, one resource, and one day.

The audited row counts were:

| Stage | Rows |
|---|---:|
| Raw source rows | 10,655,280 |
| After removing exact duplicate rows | 9,868,110 |
| After aggregation at the agreed grain | 8,459,320 |

These operations are documented in `scripts/prepare_interactions.py`. The raw ZIP archive is not modified.

### 3.7 `vle.csv`

| Field | Meaning |
|---|---|
| `id_site` | Virtual learning environment resource identifier |
| `code_module` | Course module identifier |
| `code_presentation` | Course presentation identifier |
| `activity_type` | Type of learning resource or activity |
| `week_from` | Recorded starting week, when available |
| `week_to` | Recorded ending week, when available |

**Record grain:** a resource record associated with a course presentation.

This table provides metadata that can later help interpret engagement by resource type. The current Django `Interaction` model stores the resource identifier and daily click count; it does not currently expose all VLE metadata as model fields.

## 4. Django Model Mapping

The application uses five models to represent the imported information.

| Django model | Main information represented | Key relationship or constraint |
|---|---|---|
| `Student` | Student identity and demographic attributes | Unique `id_student` |
| `Course` | Course presentation | Unique `code_module` + `code_presentation` |
| `Enrollment` | Student participation in a course presentation | Unique student + course |
| `Assessment` | Assessment record for an enrolment | Unique enrolment + assessment identifier |
| `Interaction` | Aggregated daily activity for a resource | Unique enrolment + resource + date |

### Why is there an `Enrollment` model?

A student can take more than one course presentation, and characteristics such as age band or final result can vary between enrolments.

The `Enrollment` model allows the application to represent these course-specific records without duplicating the student's identity.

It also gives assessments and interactions a clear connection to the relevant enrolment and course presentation.

## 5. Data Quality Findings

The completed audit identified the following important findings.

| Finding | Observed result | Treatment |
|---|---|---|
| Missing `imd_band` | 1,111 values | Preserve as missing; the Django field permits a blank value |
| Missing assessment dates | 11, all exams | Preserve as missing |
| Missing assessment scores | 173 | Preserve as missing, not zero |
| Exact duplicate `studentVle` rows | 787,170 | Remove during interaction preparation |
| Repeated observations at the interaction grain | Present | Aggregate click counts |
| Students with different age bands across enrolments | 72 students | Store age band at enrolment level |

Missing values should be handled according to the meaning of the field and the intended analysis. They should not all be replaced using the same rule.

## 6. Import Validation

The completed local database import produced these record counts:

| Django model | Imported records |
|---|---:|
| `Student` | 28,785 |
| `Course` | 22 |
| `Enrollment` | 32,593 |
| `Assessment` | 173,912 |
| `Interaction` | 8,459,320 |

Validation confirmed that the imported enrolments, assessments, and interactions had the required foreign-key relationships.

The total recorded click count was also checked:

| Source | Total clicks |
|---|---:|
| Prepared interaction CSV | 38,343,063 |
| Django database | 38,343,063 |

The totals matched.

**Validation limitation:** matching row counts, foreign-key checks, and aggregate click totals are useful consistency checks, but they do not prove that every individual imported interaction matches its corresponding CSV row. A row-by-row comparison has not been established by these checks.

## 7. Analytical Notes

- OULAD dates are relative day offsets, not calendar dates.
- A missing score must not be interpreted as a score of zero.
- A high click count does not necessarily mean that a student has learned more.
- Engagement and academic outcomes may be associated without one causing the other.
- Risk indicators should be defined transparently and evaluated before being used to guide decisions about individual students.
- Demographic information should be handled carefully and should not be used to make unsupported assumptions about individual students.

## 8. Current Scope and Next Phase

The source data have been audited, interaction data prepared, Django models migrated, and data imported and validated using the checks described above. The REST API and Phase 6 descriptive engagement analytics are implemented and covered by the current automated test suite.

The next phase is to define and validate early-withdrawal risk indicators using an explicit prediction cutoff and only information available by that cutoff. The dashboard and evidence-grounded query agent remain later development tasks.
