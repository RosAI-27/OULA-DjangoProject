import os
import sys
import django

from collections import defaultdict
from statistics import mean, median

from django.db.models import Count, Q, F, Sum, Value
from django.db.models.functions import Coalesce


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from analytics.models import Enrollment


def get_enrollment_engagement():
    """Return engagement metrics for every enrollment."""

    interaction_window = (
        Q(interactions__date__gte=F("date_registration"))
        & (
            Q(date_unregistration__isnull=True)
            | Q(interactions__date__lte=F("date_unregistration"))
        )
        & Q(
            interactions__date__lte=F(
                "course__module_presentation_length"
            )
        )
    )

    enrollments = (
        Enrollment.objects
        .annotate(
            interaction_records=Count(
                "interactions",
                filter=interaction_window,
            ),
            total_clicks=Coalesce(
                Sum(
                    "interactions__total_clicks",
                    filter=interaction_window,
                ),
                Value(0),
            ),
            active_days=Count(
                "interactions__date",
                filter=interaction_window,
                distinct=True,
            ),
            distinct_resources=Count(
                "interactions__id_site",
                filter=interaction_window,
                distinct=True,
            ),
        )
        .values(
            "id",
            "final_result",
            "date_registration",
            "date_unregistration",
            "course__module_presentation_length",
            "interaction_records",
            "total_clicks",
            "active_days",
            "distinct_resources",
        )
        .order_by("id")
    )

    return list(enrollments)


def calculate_registration_window(row):
    """Calculate the student's registration window in days."""

    registration = row["date_registration"]
    unregistration = row["date_unregistration"]
    presentation_length = row["course__module_presentation_length"]
    final_result = row["final_result"]

    if registration is None:
        return None, "missing_registration"

    if unregistration is None:
        if final_result == "Withdrawn":
            return None, "withdrawn_missing_unregistration"
        end_day = presentation_length
    else:
        end_day = min(unregistration, presentation_length)

    window_days = end_day - registration

    if window_days < 0:
        return None, "invalid_registration_window"

    return window_days, "valid"


def add_derived_metrics(data):
    """Add registration-window-adjusted engagement metrics."""

    for row in data:
        window_days, window_status = calculate_registration_window(row)

        row["registration_window_days"] = window_days
        row["registration_window_status"] = window_status

        if window_days is not None and window_days > 0:
            row["clicks_per_registration_day"] = (
                row["total_clicks"] / window_days
            )
            row["active_day_ratio"] = (
                row["active_days"] / window_days
            )
        else:
            row["clicks_per_registration_day"] = None
            row["active_day_ratio"] = None

    return data


def summarize_metric(values):
    """Return mean and median for a non-empty list."""

    return {
        "mean": mean(values),
        "median": median(values),
    }


def summarize_by_outcome(data):
    """Compare engagement metrics across final outcomes."""

    groups = defaultdict(list)

    for row in data:
        groups[row["final_result"]].append(row)

    outcomes = ["Distinction", "Pass", "Fail", "Withdrawn"]

    raw_metrics = [
        "total_clicks",
        "active_days",
        "distinct_resources",
        "interaction_records",
    ]

    adjusted_metrics = [
        "registration_window_days",
        "clicks_per_registration_day",
        "active_day_ratio",
    ]

    for outcome in outcomes:
        enrollments = groups[outcome]
        total_enrollments = len(enrollments)

        observed = [
            row for row in enrollments
            if row["interaction_records"] > 0
        ]

        observed_count = len(observed)
        interaction_coverage = (
            observed_count / total_enrollments * 100
            if total_enrollments > 0 else 0
        )

        valid_exposure = [
            row for row in enrollments
            if row["registration_window_days"] is not None
        ]

        exposure_count = len(valid_exposure)
        exposure_coverage = (
            exposure_count / total_enrollments * 100
            if total_enrollments > 0 else 0
        )

        withdrawn_missing_unregistration = sum(
            1
            for row in enrollments
            if row["registration_window_status"]
            == "withdrawn_missing_unregistration"
        )

        print(f"\n{'=' * 65}")
        print(f"OUTCOME: {outcome.upper()}")
        print(f"{'=' * 65}")
        print(f"Total enrollments: {total_enrollments}")
        print(f"With recorded interactions: {observed_count}")
        print(
            f"Without recorded interactions: "
            f"{total_enrollments - observed_count}"
        )
        print(f"Interaction coverage: {interaction_coverage:.2f}%")
        print(
            f"Valid registration-window records: "
            f"{exposure_count}"
        )
        print(f"Registration-window coverage: {exposure_coverage:.2f}%")

        if withdrawn_missing_unregistration:
            print(
                "Withdrawn with missing unregistration date: "
                f"{withdrawn_missing_unregistration}"
            )

        if observed:
            print("\nRAW ENGAGEMENT METRICS")
            print("-" * 65)

            for metric in raw_metrics:
                values = [row[metric] for row in observed]
                summary = summarize_metric(values)
                print(
                    f"{metric}: "
                    f"mean = {summary['mean']:.2f}, "
                    f"median = {summary['median']:.2f}"
                )

        if valid_exposure:
            print("\nREGISTRATION-WINDOW-ADJUSTED METRICS")
            print("-" * 65)

            for metric in adjusted_metrics:
                values = [
                    row[metric]
                    for row in valid_exposure
                    if row[metric] is not None
                ]

                if not values:
                    continue

                summary = summarize_metric(values)
                print(
                    f"{metric}: "
                    f"mean = {summary['mean']:.4f}, "
                    f"median = {summary['median']:.4f}"
                )


if __name__ == "__main__":
    data = get_enrollment_engagement()
    data = add_derived_metrics(data)

    print(f"Total enrollments analyzed: {len(data)}")

    enrollments_with_interactions = sum(
        1 for row in data if row["interaction_records"] > 0
    )
    enrollments_without_interactions = (
        len(data) - enrollments_with_interactions
    )
    valid_exposure_records = sum(
        1
        for row in data
        if row["registration_window_days"] is not None
    )
    withdrawn_missing_unregistration = sum(
        1
        for row in data
        if row["registration_window_status"]
        == "withdrawn_missing_unregistration"
    )

    print(
        "Enrollments with recorded interactions: "
        f"{enrollments_with_interactions}"
    )
    print(
        "Enrollments without recorded interactions: "
        f"{enrollments_without_interactions}"
    )
    print(
        "Enrollments with valid registration window: "
        f"{valid_exposure_records}"
    )
    print(
        "Withdrawn enrollments with missing unregistration date: "
        f"{withdrawn_missing_unregistration}"
    )

    summarize_by_outcome(data)
