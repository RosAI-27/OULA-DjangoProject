# Engagement Analysis

## 1. Objective

This analysis examines how recorded Virtual Learning Environment (VLE) activity varies across student outcomes and course presentations in the Open University Learning Analytics Dataset (OULAD).

It is descriptive and exploratory. It does not establish that VLE activity causes a particular academic outcome.

## 2. Analytical grain and population

The primary analytical unit is one student enrollment in one course presentation.

The analysis starts from the Enrollment table rather than the Interaction table. This preserves enrollments with no recorded VLE interactions.

Course-level analyses group results by:
- Course module (`code_module`)
- Course presentation (`code_presentation`)

Outcome-level analyses additionally group by `final_result`.

## 3. Engagement indicators

The analysis uses the following indicators:

| Indicator | Meaning |
|---|---|
| Total clicks | Sum of recorded VLE clicks |
| Active days | Number of distinct days with recorded interactions |
| Distinct resources | Number of distinct VLE resources accessed |
| Interaction records | Number of aggregated student-resource-day records |
| Clicks per registration-window day | Recorded clicks divided by the valid registration-window duration |
| Active-day ratio | Active days divided by the valid registration-window duration |

These indicators describe recorded platform activity. They are proxies for engagement, not direct measurements of attention, learning, or effort.

## 4. Registration-window adjustment

Raw interaction totals can be affected by how long a student was registered. To make comparisons more informative, the analysis also calculates activity within each enrollment's valid registration window.

An interaction is included in the adjusted metrics when:
- Its date is on or after the student's registration date.
- It is on or before the unregistration date, when that date exists.
- It does not exceed the course presentation length.

For enrollments without an unregistration date and without a Withdrawn outcome, the presentation end is used as the window end.

For Withdrawn enrollments with a missing unregistration date, the end of the registration window is unknown. Their adjusted window metrics are therefore treated as unavailable, not zero.

The window duration is calculated from the registration date to the selected window end. A zero-day or invalid window does not produce a rate.

**Important limitation:** this is a registration-window-adjusted activity measure, not a measure of actual VLE exposure. Registration dates and VLE availability do not necessarily coincide. The denominator should therefore not be interpreted as the exact number of days a student had access to, or used, the learning platform.

## 5. Missing values and data quality

Missing values are not automatically replaced with zero.

In particular:
- A missing score is not interpreted as a score of zero.
- A missing unregistration date for a Withdrawn enrollment does not provide a known withdrawal date.
- An enrollment without recorded interactions is retained in the analysis.
- Missing adjusted metrics are distinguished from observed zero activity.

The source data contain 93 Withdrawn enrollments with missing unregistration dates. Their adjusted registration-window metrics are unavailable.

The analysis also checks that filtered interaction totals do not exceed their corresponding raw totals.

## 6. Distribution analysis

Engagement indicators are summarized using percentiles (P10, P25, P50, P75, P90 and P95), both overall and by final outcome.

Medians and percentiles are emphasized because engagement measures are skewed and can contain substantial differences between students.

The distribution analysis is implemented in:

- `scripts/analyze_engagement_distributions.py`

## 7. Course variation

Course presentation comparisons examine differences in median activity, the percentage of enrollments without recorded interactions, and the percentage with valid registration windows.

The analysis covers 22 course presentations and 32,593 enrollments.

Results are exported to:

- `reports/course_engagement_variation.csv`

Differences between courses may reflect course design, resource availability, student composition, or other contextual factors. They should not automatically be interpreted as differences in course difficulty or student motivation.

Implemented in:

- `scripts/analyze_course_variation.py`

## 8. Engagement by outcome within courses

The analysis also compares engagement indicators across outcomes within each course presentation.

This helps assess whether the broad association between recorded activity and outcomes is also visible within individual course presentations.

Results are exported to:

- `reports/course_engagement_by_outcome.csv`

Some course-outcome groups are small. The report flags groups with fewer than 30 enrollments; their medians should be interpreted cautiously.

Implemented in:

- `scripts/analyze_engagement_by_course_outcome.py`

## 9. Interpretation and limitations

The descriptive analysis shows that students with Distinction or Pass outcomes generally have higher recorded VLE activity than students who Fail or Withdraw.

However:
- Association does not establish causation.
- Click counts do not measure the quality of learning.
- Course presentations differ in their activity patterns.
- Students may engage with learning materials outside the VLE.
- Withdrawal can occur at different points in a course.
- Final outcomes and full-course activity cannot be used as early-warning predictors without introducing information that would not have been available at the prediction time.

The findings are therefore useful for exploratory analysis and for motivating a carefully designed early-warning experiment. They are not, by themselves, a validated student-risk model.

## 10. Reproducibility

Run the analysis scripts from the project root with the project's Python environment activated.

The scripts use the imported Django database and generate aggregate CSV reports in `reports/`.

Raw and processed student-level datasets, environment files, and the local SQLite database should remain excluded from version control.
