
"""Audit selected OULAD missing values without modifying source data."""

from pathlib import Path
import zipfile

import pandas as pd


ZIP_PATH = Path("data/raw/OULA.zip")
DATA_FOLDER = "anonymiseddata/"


def read_oulad_csv(archive, filename):
    """Read one CSV from the OULAD ZIP archive."""
    path = DATA_FOLDER + filename
    with archive.open(path) as file:
        return pd.read_csv(file)


def main():
    if not ZIP_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {ZIP_PATH.resolve()}. "
            "Run this script from the repository root."
        )

    with zipfile.ZipFile(ZIP_PATH) as archive:
        student_info = read_oulad_csv(archive, "studentInfo.csv")
        registration = read_oulad_csv(
            archive, "studentRegistration.csv"
        )
        assessments = read_oulad_csv(archive, "assessments.csv")
        results = read_oulad_csv(
            archive, "studentAssessment.csv"
        )

    enrollment_key = [
        "code_module",
        "code_presentation",
        "id_student",
    ]


    # Confirm that studentInfo and registration can be matched
    # without multiplying or losing enrollment records.
    if student_info.duplicated(enrollment_key).any():
        raise ValueError("Duplicate enrollment keys in studentInfo.")

    if registration.duplicated(enrollment_key).any():
        raise ValueError("Duplicate enrollment keys in registration.")

    enrollment = student_info[
        enrollment_key + ["final_result"]
    ].merge(
        registration[
            enrollment_key
            + ["date_registration", "date_unregistration"]
        ],
        on=enrollment_key,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    print("\n=== 1. ENROLLMENT MATCHING ===")
    print(enrollment["_merge"].value_counts().to_string())

    matched = enrollment[enrollment["_merge"] == "both"].copy()

    # Missing date_unregistration versus recorded final outcome.
    matched["unregistration_date_missing"] = (
        matched["date_unregistration"].isna()
    )

    print("\n=== 2. UNREGISTRATION DATE VS FINAL RESULT ===")
    print(
        pd.crosstab(
            matched["unregistration_date_missing"],
            matched["final_result"],
            margins=True,
        ).to_string()
    )
    print(
        "\nRows: True means date_unregistration is missing; "
        "False means a date is recorded."
    )

    print("\n=== 3. MISSING REGISTRATION DATES ===")
    print(
        "Missing date_registration:",
        int(matched["date_registration"].isna().sum()),
    )

    # Assessment score missingness, joined to assessment metadata.
    if assessments["id_assessment"].duplicated().any():
        raise ValueError("Duplicate id_assessment in assessments.")

    score_data = results.merge(
        assessments[
            [
                "id_assessment",
                "code_module",
                "code_presentation",
                "assessment_type",
                "date",
            ]
        ],
        on="id_assessment",
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    print("\n=== 4. ASSESSMENT SCORE MISSINGNESS ===")
    print("Assessment result rows:", len(score_data))
    print("Missing scores:", int(score_data["score"].isna().sum()))
    print("Unmatched assessment IDs:", int(
        (score_data["_merge"] == "left_only").sum()
    ))

    print("\nMissing scores by assessment type:")
    print(
        score_data.groupby("assessment_type", dropna=False)["score"]
        .agg(
            total_rows="size",
            missing_scores=lambda s: int(s.isna().sum()),
        )
        .to_string()
    )

    print("\nMissing scores by module and presentation:")
    print(
        score_data.groupby(
            ["code_module", "code_presentation"],
            dropna=False,
        )["score"]
        .agg(
            total_rows="size",
            missing_scores=lambda s: int(s.isna().sum()),
        )
        .to_string()
    )

    print("\n=== 5. MISSING ASSESSMENT DATES ===")
    print("Missing assessment dates:", int(assessments["date"].isna().sum()))
    print("\nMissing dates by assessment type:")
    print(
        assessments.assign(
            date_missing=assessments["date"].isna()
        )
        .groupby("assessment_type", dropna=False)["date_missing"]
        .agg(total_assessments="size", missing_dates="sum")
        .to_string()
    )


    print("\n=== 6. UNREGISTRATION EXCEPTIONS ===")

    failed_with_date = matched[
        matched["date_unregistration"].notna()
        & (matched["final_result"] != "Withdrawn")
    ]

    withdrawn_without_date = matched[
        matched["date_unregistration"].isna()
        & (matched["final_result"] == "Withdrawn")
    ]

    print("Recorded unregistration date but not Withdrawn:")
    print(failed_with_date[
        enrollment_key + ["final_result", "date_unregistration"]
    ].to_string(index=False))

    print("\nWithdrawn without recorded unregistration date:")
    print(withdrawn_without_date[
        enrollment_key + ["final_result", "date_registration"]
    ].to_string(index=False))

    print("\n=== 7. MISSING REGISTRATION DATE RECORDS ===")

    missing_registration = matched[
        matched["date_registration"].isna()
    ]

    print(
        missing_registration[
            enrollment_key
            + ["final_result", "date_unregistration"]
        ].to_string(index=False)
    )

    print("\n=== 8. MISSING TMA SCORES: SAMPLE ===")

    missing_scores = score_data[score_data["score"].isna()]

    print(
        missing_scores[
            [
                "id_assessment",
                "id_student",
                "assessment_type",
                "date",
                "date_submitted",
                "is_banked",
                "score",
            ]
        ].head(15).to_string(index=False)
    )


    print("\n=== 9. MISSING TMA SCORE DIAGNOSTICS ===")

    missing_scores = score_data[
        score_data["score"].isna()
    ].copy()

    print("\nMissing scores by is_banked:")
    print(
        missing_scores["is_banked"]
        .value_counts(dropna=False)
        .sort_index()
    )

    print(
        "\nMissing date_submitted:",
        missing_scores["date_submitted"].isna().sum()
    )

    comparable = missing_scores.dropna(
        subset=["date", "date_submitted"]
    ).copy()

    comparable["submitted_after_due_date"] = (
        comparable["date_submitted"] > comparable["date"]
    )

    print("\nMissing scores by submission timing:")
    print(
        comparable["submitted_after_due_date"]
        .value_counts(dropna=False)
        .rename(index={
            True: "Submitted after assessment date",
            False: "Submitted on or before assessment date"
        })
    )


    print("\n=== 10. TMA SCORE MISSINGNESS BY TIMING ===")

    tma = score_data[
        score_data["assessment_type"] == "TMA"
    ].copy()

    tma["score_missing"] = tma["score"].isna()

    comparable_tma = tma.dropna(
        subset=["date", "date_submitted"]
    ).copy()

    comparable_tma["submitted_after_due_date"] = (
        comparable_tma["date_submitted"] > comparable_tma["date"]
    )

    timing_summary = (
        comparable_tma
        .groupby("submitted_after_due_date")["score_missing"]
        .agg(
            total_records="count",
            missing_scores="sum",
            missing_score_rate="mean"
        )
    )

    timing_summary.index = timing_summary.index.map({
        True: "After assessment date",
        False: "On or before assessment date"
    })

    timing_summary["missing_score_rate"] = (
        timing_summary["missing_score_rate"] * 100
    ).round(2)

    print(timing_summary)
    print(
        "\nTMA records excluded because timing was unavailable:",
        len(tma) - len(comparable_tma)
    )


if __name__ == "__main__":
    main()
