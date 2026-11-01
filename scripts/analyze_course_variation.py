
"""Analyze engagement variation across OULAD course presentations."""

from analyze_engagement_distributions import (
    load_engagement_data,
    calculate_adjusted_metrics,
)


def analyze_course_variation(df):
    """Summarize engagement metrics for each course presentation."""

    results = (
        df.groupby(
            [
                "course__code_module",
                "course__code_presentation",
            ],
            dropna=False,
        )
        .agg(
            enrollments=("id", "count"),

            # Raw interaction coverage
            enrollments_without_interactions=(
                "interaction_records",
                lambda x: (x == 0).sum(),
            ),

            # Registration-window coverage
            valid_registration_windows=(
                "registration_window_days",
                "count",
            ),

            # Raw engagement
            median_total_clicks=("total_clicks", "median"),
            median_active_days=("active_days", "median"),

            # Registration-window-adjusted engagement
            median_window_clicks=("window_total_clicks", "median"),
            median_window_active_days=("window_active_days", "median"),
            median_clicks_per_day=(
                "clicks_per_registration_day",
                "median",
            ),
            median_active_day_ratio=("active_day_ratio", "median"),
        )
        .reset_index()
    )

    # Calculate percentages after aggregation.
    results["no_interaction_pct"] = (
        results["enrollments_without_interactions"]
        / results["enrollments"]
        * 100
    )

    results["valid_window_pct"] = (
        results["valid_registration_windows"]
        / results["enrollments"]
        * 100
    )

    return results


def display_course_results(results):
    """Display course-level engagement comparisons."""

    print("\n" + "=" * 90)
    print("COURSE PRESENTATION ENGAGEMENT ANALYSIS")
    print("=" * 90)

    print(f"\nNumber of course presentations: {len(results)}")
    print(f"Total enrollments: {results['enrollments'].sum():,}")

    columns = [
        "course__code_module",
        "course__code_presentation",
        "enrollments",
        "no_interaction_pct",
        "valid_window_pct",
        "median_total_clicks",
        "median_active_days",
        "median_window_clicks",
        "median_window_active_days",
        "median_clicks_per_day",
        "median_active_day_ratio",
    ]

    print("\nENGAGEMENT BY COURSE PRESENTATION\n")

    print(
        results[columns]
        .sort_values(
            ["course__code_module", "course__code_presentation"]
        )
        .round(3)
        .to_string(index=False)
    )

    # Compare the range of course-level median activity.
    comparison_metrics = [
        "median_total_clicks",
        "median_active_days",
        "median_clicks_per_day",
        "median_active_day_ratio",
    ]

    print("\n" + "=" * 90)
    print("VARIATION ACROSS COURSE PRESENTATIONS")
    print("=" * 90)

    for metric in comparison_metrics:
        print(f"\n{metric}")
        print(f"  Lowest course median: {results[metric].min():.3f}")
        print(f"  Highest course median: {results[metric].max():.3f}")
        print(f"  Overall course-median average: {results[metric].mean():.3f}")


def main():
    print("Loading enrollment and interaction data...")

    df = load_engagement_data()
    df = calculate_adjusted_metrics(df)

    print("Analyzing course presentation variation...")

    results = analyze_course_variation(df)

    display_course_results(results)

    # Save the results for later documentation and comparison.
    output_path = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "reports"
        / "course_engagement_variation.csv"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    results.to_csv(output_path, index=False)

    print(f"\nResults saved to: {output_path}")
    print("\nAnalysis completed successfully.")


if __name__ == "__main__":
    main()
