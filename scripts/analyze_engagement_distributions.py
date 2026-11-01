
"""Analyze OULAD engagement distributions by final enrollment outcome.

The analysis preserves all enrollments and calculates interaction metrics
within each student's registration window.

Important:
- This is retrospective descriptive analysis, not an early-warning model.
- Registration-window-adjusted activity is not a measure of actual study time.
"""

import os
import sys
from pathlib import Path

import django
import numpy as np
import pandas as pd

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce



# 1. Initialize Django


BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from analytics.models import Enrollment



# 2. Load enrollment and engagement data


def load_engagement_data():
    """Retrieve raw and registration-window-filtered engagement metrics."""

    window_filter = (
        Q(interactions__date__gte=F("date_registration"))
        & Q(
            interactions__date__lte=F(
                "course__module_presentation_length"
            )
        )
        & (
            (
                Q(date_unregistration__isnull=True)
                & ~Q(final_result="Withdrawn")
            )
            | Q(interactions__date__lte=F("date_unregistration"))
        )
    )

    enrollments = Enrollment.objects.annotate(
        # Raw interaction metrics
        interaction_records=Count("interactions"),
        total_clicks=Coalesce(
            Sum("interactions__total_clicks"), 0
        ),
        active_days=Count(
            "interactions__date",
            distinct=True,
        ),
        distinct_resources=Count(
            "interactions__id_site",
            distinct=True,
        ),

        # Metrics restricted to the registration window
        window_interaction_records=Count(
            "interactions",
            filter=window_filter,
        ),
        window_total_clicks=Coalesce(
            Sum(
                "interactions__total_clicks",
                filter=window_filter,
            ),
            0,
        ),
        window_active_days=Count(
            "interactions__date",
            distinct=True,
            filter=window_filter,
        ),
        window_distinct_resources=Count(
            "interactions__id_site",
            distinct=True,
            filter=window_filter,
        ),
    ).values(
        "id",
        "final_result",
        "course__code_module",
        "course__code_presentation",
        "interaction_records",
        "total_clicks",
        "active_days",
        "distinct_resources",
        "window_interaction_records",
        "window_total_clicks",
        "window_active_days",
        "window_distinct_resources",
        "date_registration",
        "date_unregistration",
        "course__module_presentation_length",
    )

    return pd.DataFrame.from_records(enrollments)



# 3. Calculate registration-window-adjusted metrics


def calculate_adjusted_metrics(df):
    """Calculate activity relative to each enrollment's registration window."""

    df = df.copy()

    presentation_end = df["course__module_presentation_length"]

    # Use the course end when unregistration is missing.
    df["window_end"] = df["date_unregistration"].fillna(
        presentation_end
    )

    # Never extend the window beyond the presentation length.
    df["window_end"] = df["window_end"].clip(
        upper=presentation_end
    )

    # Do not invent an end date for withdrawn enrollments whose unregistration date is missing.
    missing_withdrawal_date = (
        (df["final_result"] == "Withdrawn")
        & df["date_unregistration"].isna()
    )

        # Registration-window activity cannot be determined when a withdrawn student has no recorded unregistration date.
    window_metrics = [
        "window_interaction_records",
        "window_total_clicks",
        "window_active_days",
        "window_distinct_resources",
    ]

    df.loc[missing_withdrawal_date, window_metrics] = np.nan

    df.loc[missing_withdrawal_date, "window_end"] = np.nan

    df["registration_window_days"] = (
        df["window_end"] - df["date_registration"]
    )

    valid_window = (
        df["date_registration"].notna()
        & df["registration_window_days"].ge(0)
    )

    df.loc[
        ~valid_window,
        "registration_window_days"
    ] = np.nan

    denominator = df["registration_window_days"].replace(
        0, np.nan
    )

    df["clicks_per_registration_day"] = (
        df["window_total_clicks"] / denominator
    )

    df["active_day_ratio"] = (
        df["window_active_days"] / denominator
    )

    return df



# 4. Display validation information


def validate_data(df):
    """Check key counts and data consistency."""

    print("\n" + "=" * 65)
    print("DATA VALIDATION")
    print("=" * 65)

    print(f"Total enrollments: {len(df):,}")

    print(
        "Enrollments with valid registration windows:",
        f"{df['registration_window_days'].notna().sum():,}",
    )

    missing_withdrawal_date = (
        (df["final_result"] == "Withdrawn")
        & df["date_unregistration"].isna()
    )

    print(
        "Withdrawn enrollments with missing unregistration dates:",
        f"{missing_withdrawal_date.sum():,}",
    )

    print(
        "Enrollments without raw interaction records:",
        f"{(df['interaction_records'] == 0).sum():,}",
    )

    # Check that filtered activity does not exceed raw activity.
    valid_window_metrics = df["window_interaction_records"].notna()

    checks = {
        "Filtered clicks <= raw clicks": (
            df.loc[valid_window_metrics, "window_total_clicks"]
            <= df.loc[valid_window_metrics, "total_clicks"]
        ).all(),
        "Filtered records <= raw records": (
            df.loc[valid_window_metrics, "window_interaction_records"]
            <= df.loc[valid_window_metrics, "interaction_records"]
        ).all(),
        "Filtered active days <= raw active days": (
            df.loc[valid_window_metrics, "window_active_days"]
            <= df.loc[valid_window_metrics, "active_days"]
        ).all(),
    }

    print("\nConsistency checks:")

    for description, passed in checks.items():
        print(f"{description}: {passed}")

    if not all(checks.values()):
        raise ValueError("One or more data consistency checks failed.")



# 5. Calculate percentile distributions


METRICS = [
    "total_clicks",
    "active_days",
    "distinct_resources",
    "interaction_records",
    "window_total_clicks",
    "window_active_days",
    "window_distinct_resources",
    "window_interaction_records",
    "registration_window_days",
    "clicks_per_registration_day",
    "active_day_ratio",
]

PERCENTILES = [
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
    0.95,
]


def calculate_percentiles(df, group_column=None):
    """Calculate selected percentiles for engagement metrics."""

    available_metrics = [
        metric for metric in METRICS if metric in df.columns
    ]

    if group_column:
        result = (
            df.groupby(group_column)[available_metrics]
            .quantile(PERCENTILES)
            .unstack()
        )
    else:
        result = df[available_metrics].quantile(PERCENTILES)

    return result



# 6. Generate analysis output


def main():
    df = load_engagement_data()

    df = calculate_adjusted_metrics(df)

    validate_data(df)

    print("\n" + "=" * 65)
    print("OVERALL ENGAGEMENT DISTRIBUTIONS")
    print("=" * 65)

    overall = calculate_percentiles(df)

    print(overall.round(3).to_string())

    print("\n" + "=" * 65)
    print("ENGAGEMENT DISTRIBUTIONS BY FINAL OUTCOME")
    print("=" * 65)

    by_outcome = calculate_percentiles(
        df,
        group_column="final_result",
    )

    print(by_outcome.round(3).to_string())

    print("\n" + "=" * 65)
    print("ENROLLMENT COUNTS BY OUTCOME")
    print("=" * 65)

    print(
        df["final_result"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nAnalysis completed successfully.")


if __name__ == "__main__":
    main()
