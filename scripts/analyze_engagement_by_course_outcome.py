
"""Compare engagement metrics by final outcome within each OULAD course presentation.

This is retrospective descriptive analysis. It does not establish causality
or produce early-warning predictions.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from analyze_engagement_distributions import (
    load_engagement_data,
    calculate_adjusted_metrics,
)

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"

GROUP_COLUMNS = [
    "course__code_module",
    "course__code_presentation",
    "final_result",
]

METRICS = [
    "total_clicks",
    "active_days",
    "distinct_resources",
    "interaction_records",
    "window_total_clicks",
    "window_active_days",
    "window_distinct_resources",
    "window_interaction_records",
    "clicks_per_registration_day",
    "active_day_ratio",
]


def analyze_by_course_outcome(df):
    """Calculate engagement summaries within each course presentation."""

    df = df.copy()

    df["no_interaction"] = df["interaction_records"].eq(0)

    summary = (
        df.groupby(GROUP_COLUMNS, dropna=False)
        .agg(
            enrollments=("id", "count"),
            no_interaction_count=("no_interaction", "sum"),
            median_total_clicks=("total_clicks", "median"),
            median_active_days=("active_days", "median"),
            median_distinct_resources=("distinct_resources", "median"),
            median_interaction_records=("interaction_records", "median"),
            median_window_clicks=("window_total_clicks", "median"),
            median_window_active_days=("window_active_days", "median"),
            median_clicks_per_day=("clicks_per_registration_day", "median"),
            median_active_day_ratio=("active_day_ratio", "median"),
            valid_registration_windows=("registration_window_days", "count"),
        )
        .reset_index()
    )

    summary["no_interaction_pct"] = (
        summary["no_interaction_count"]
        / summary["enrollments"]
        * 100
    )

    summary["valid_window_pct"] = (
        summary["valid_registration_windows"]
        / summary["enrollments"]
        * 100
    )

    # Small groups should be interpreted cautiously.
    summary["small_group_warning"] = np.where(
        summary["enrollments"] < 30,
        "Small group: interpret cautiously",
        "",
    )

    return summary


def validate_results(df, summary):
    """Validate enrollment coverage and grouping."""

    print("\n" + "=" * 65)
    print("VALIDATION")
    print("=" * 65)

    print(f"Source enrollments: {len(df):,}")
    print(f"Grouped enrollments: {summary['enrollments'].sum():,}")
    print(f"Number of course-outcome groups: {len(summary):,}")

    checks = {
        "All enrollments represented": (
            summary["enrollments"].sum() == len(df)
        ),
        "No duplicated course-outcome groups": (
            not summary.duplicated(GROUP_COLUMNS).any()
        ),
        "Filtered clicks <= raw clicks": (
            df.loc[
                df["window_total_clicks"].notna(),
                "window_total_clicks",
            ]
            <= df.loc[
                df["window_total_clicks"].notna(),
                "total_clicks",
            ]
        ).all(),
    }

    for description, passed in checks.items():
        print(f"{description}: {passed}")

    if not all(checks.values()):
        raise ValueError("Validation failed.")


def main():
    df = load_engagement_data()
    df = calculate_adjusted_metrics(df)

    summary = analyze_by_course_outcome(df)

    validate_results(df, summary)

    display_columns = GROUP_COLUMNS + [
        "enrollments",
        "no_interaction_pct",
        "valid_window_pct",
        "median_total_clicks",
        "median_active_days",
        "median_window_clicks",
        "median_window_active_days",
        "median_clicks_per_day",
        "median_active_day_ratio",
        "small_group_warning",
    ]

    print("\n" + "=" * 65)
    print("ENGAGEMENT BY COURSE PRESENTATION AND FINAL OUTCOME")
    print("=" * 65)

    print(
        summary[display_columns]
        .round(3)
        .to_string(index=False)
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORTS_DIR / "course_engagement_by_outcome.csv"
    summary.to_csv(output_path, index=False)

    print(f"\nReport saved to: {output_path}")
    print("\nAnalysis completed successfully.")


if __name__ == "__main__":
    main()
