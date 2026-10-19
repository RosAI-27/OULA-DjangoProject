"""Prepare the OULAD studentVle data at the agreed Interaction grain.

Grain:
    one student + one course presentation + one VLE resource + one day

The raw ZIP is never modified. The script removes only exact duplicate source
rows, then aggregates repeated student-resource-day observations by summing
sum_click into total_clicks.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

import pandas as pd


KEY_COLUMNS = [
    "code_module",
    "code_presentation",
    "id_student",
    "id_site",
    "date",
]

REQUIRED_COLUMNS = KEY_COLUMNS + ["sum_click"]


def prepare_interactions(zip_path: Path, output_path: Path) -> None:
    """Read raw OULAD data, validate it, aggregate it, and write a CSV."""
    with zipfile.ZipFile(zip_path) as archive:
        source_name = "anonymiseddata/studentVle.csv"
        if source_name not in archive.namelist():
            source_name = "studentVle.csv"

        with archive.open(source_name) as source:
            df = pd.read_csv(source)

    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    raw_rows = len(df)
    exact_duplicates = int(df.duplicated().sum())

    # Remove only truly identical source rows.
    df = df.drop_duplicates()
    deduplicated_rows = len(df)

    # The application grain is student-resource-day within a course presentation.
    interactions = (
        df.groupby(KEY_COLUMNS, as_index=False, sort=False)["sum_click"]
        .sum()
        .rename(columns={"sum_click": "total_clicks"})
    )

    if (interactions["total_clicks"] < 0).any():
        raise ValueError("Aggregated total_clicks contains a negative value.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    interactions.to_csv(output_path, index=False)

    print(f"Raw rows: {raw_rows:,}")
    print(f"Exact duplicate rows removed: {exact_duplicates:,}")
    print(f"Rows after exact de-duplication: {deduplicated_rows:,}")
    print(f"Processed Interaction rows: {len(interactions):,}")
    print(
        "Reduction from raw: "
        f"{(1 - len(interactions) / raw_rows) * 100:.2f}%"
    )
    print(
        "Reduction after exact de-duplication: "
        f"{(1 - len(interactions) / deduplicated_rows) * 100:.2f}%"
    )
    print(f"Output: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/OULA.zip"),
        help="Path to the raw OULAD ZIP file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/interactions.csv"),
        help="Path for the processed Interaction CSV.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    prepare_interactions(args.input, args.output)
