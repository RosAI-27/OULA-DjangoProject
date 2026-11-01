
import zipfile
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from analytics.models import (
    Assessment,
    Course,
    Enrollment,
    Interaction,
    Student,
)


BATCH_SIZE = 2000
CHUNK_SIZE = 50000

STUDENT_FIELDS = [
    "gender",
    "region",
    "highest_education",
    "imd_band",
    "disability",
]


def read_source_csv(archive, filename):
    """Read one CSV from the OULAD archive."""
    path = f"anonymiseddata/{filename}"

    try:
        with archive.open(path) as file:
            return pd.read_csv(file)
    except KeyError as exc:
        raise CommandError(f"Missing source file: {path}") from exc


def optional_int(value):
    """Convert a value to int, preserving missing values as None."""
    if pd.isna(value):
        return None
    return int(value)


def require_columns(frame, columns, filename):
    """Fail clearly if a required column is absent."""
    missing = set(columns) - set(frame.columns)
    if missing:
        raise CommandError(
            f"{filename} is missing columns: {sorted(missing)}"
        )


class Command(BaseCommand):
    help = "Import OULAD data into the analytics database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help=(
                "Delete existing analytics data and rebuild it. "
                "Use this to restart an interrupted import."
            ),
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=CHUNK_SIZE,
            help="Number of interaction CSV rows read at a time.",
        )

    def handle(self, *args, **options):
        chunk_size = options["chunk_size"]

        if chunk_size < 1:
            raise CommandError("--chunk-size must be greater than zero.")

        project_root = Path(settings.BASE_DIR).parent
        raw_zip = project_root / "data" / "raw" / "OULA.zip"
        interactions_csv = (
            project_root / "data" / "processed" / "interactions.csv"
        )

        if not raw_zip.exists():
            raise CommandError(f"Raw dataset not found: {raw_zip}")

        if not interactions_csv.exists():
            raise CommandError(
                f"Processed interactions not found: {interactions_csv}"
            )

        existing_data = any(
            model.objects.exists()
            for model in (
                Student,
                Course,
                Enrollment,
                Assessment,
                Interaction,
            )
        )

        if existing_data and not options["replace"]:
            raise CommandError(
                "Analytics tables already contain data. "
                "Use --replace to rebuild them, or inspect the database "
                "before proceeding."
            )

        self.stdout.write("Reading OULAD source tables...")

        with zipfile.ZipFile(raw_zip) as archive:
            courses_df = read_source_csv(archive, "courses.csv")
            info_df = read_source_csv(archive, "studentInfo.csv")
            registration_df = read_source_csv(
                archive, "studentRegistration.csv"
            )
            assessments_df = read_source_csv(archive, "assessments.csv")
            student_assessment_df = read_source_csv(
                archive, "studentAssessment.csv"
            )

        require_columns(
            courses_df,
            [
                "code_module",
                "code_presentation",
                "module_presentation_length",
            ],
            "courses.csv",
        )
        require_columns(
            info_df,
            [
                "code_module",
                "code_presentation",
                "id_student",
                *STUDENT_FIELDS,
                "age_band",
                "num_of_prev_attempts",
                "studied_credits",
                "final_result",
            ],
            "studentInfo.csv",
        )
        require_columns(
            registration_df,
            [
                "code_module",
                "code_presentation",
                "id_student",
                "date_registration",
                "date_unregistration",
            ],
            "studentRegistration.csv",
        )
        require_columns(
            assessments_df,
            [
                "code_module",
                "code_presentation",
                "id_assessment",
                "assessment_type",
                "date",
                "weight",
            ],
            "assessments.csv",
        )
        require_columns(
            student_assessment_df,
            [
                "id_assessment",
                "id_student",
                "date_submitted",
                "is_banked",
                "score",
            ],
            "studentAssessment.csv",
        )

        course_key = ["code_module", "code_presentation"]
        enrollment_key = [
            "id_student",
            "code_module",
            "code_presentation",
        ]

        if courses_df.duplicated(course_key).any():
            raise CommandError(
                "courses.csv contains duplicate course presentations."
            )

        if info_df.duplicated(enrollment_key).any():
            raise CommandError(
                "studentInfo.csv contains duplicate enrolment keys."
            )

        if registration_df.duplicated(enrollment_key).any():
            raise CommandError(
                "studentRegistration.csv contains duplicate enrolment keys."
            )

        # Registration dates belong to an enrolment, not a student.
        info_df = info_df.merge(
            registration_df,
            on=enrollment_key,
            how="left",
            validate="one_to_one",
            indicator=True,
        )

        unmatched_registration = info_df["_merge"] != "both"
        if unmatched_registration.any():
            raise CommandError(
                f"{int(unmatched_registration.sum())} enrolments have "
                "no matching studentRegistration record."
            )
        info_df = info_df.drop(columns="_merge")

        # Demographic attributes should be consistent for each student.
        # Blank IMD bands are treated as missing, not as a conflicting value.
        for field in STUDENT_FIELDS:
            info_df[field] = info_df[field].replace("", pd.NA)

        for field in STUDENT_FIELDS:
            conflicts = (
                info_df.groupby("id_student")[field]
                .nunique()
                .loc[lambda values: values > 1]
            )
            if not conflicts.empty:
                examples = conflicts.index[:5].tolist()
                raise CommandError(
                    f"Conflicting student values for {field}; "
                    f"example student IDs: {examples}"
                )

        students_df = info_df[
            ["id_student", *STUDENT_FIELDS]
        ].drop_duplicates("id_student").copy()

        if students_df[["id_student", "gender", "region",
                        "highest_education", "disability"]].isna().any().any():
            raise CommandError(
                "Required student identifiers or demographic fields "
                "contain missing values."
            )

        # Merge assessment metadata with individual student submissions.
        if assessments_df["id_assessment"].duplicated().any():
            raise CommandError(
                "assessments.csv contains duplicate assessment IDs."
            )

        assessment_df = student_assessment_df.merge(
            assessments_df,
            on="id_assessment",
            how="left",
            validate="many_to_one",
            indicator=True,
        )

        unmatched_assessments = assessment_df["_merge"] != "both"
        if unmatched_assessments.any():
            raise CommandError(
                f"{int(unmatched_assessments.sum())} student assessment "
                "records have no matching assessment metadata."
            )
        assessment_df = assessment_df.drop(columns="_merge")

        if assessment_df["date_submitted"].isna().any():
            raise CommandError(
                "date_submitted contains missing values, but the current "
                "Assessment model requires this field."
            )

        # Validate interaction headers before changing the database.
        interaction_header = pd.read_csv(interactions_csv, nrows=0)
        require_columns(
            interaction_header,
            [
                "code_module",
                "code_presentation",
                "id_student",
                "id_site",
                "date",
                "total_clicks",
            ],
            "interactions.csv",
        )

        self.stdout.write(
            f"Source rows: {len(courses_df):,} course presentations, "
            f"{len(students_df):,} students, "
            f"{len(info_df):,} enrolments, "
            f"{len(assessment_df):,} student assessments."
        )

        if existing_data:
            self.stdout.write(
                self.style.WARNING(
                    "--replace selected: existing analytics data "
                    "will be deleted."
                )
            )

        # Clear old data in dependency order and rebuild the small tables.
        with transaction.atomic():
            Interaction.objects.all().delete()
            Assessment.objects.all().delete()
            Enrollment.objects.all().delete()
            Student.objects.all().delete()
            Course.objects.all().delete()

            Course.objects.bulk_create(
                [
                    Course(
                        code_module=row.code_module,
                        code_presentation=row.code_presentation,
                        module_presentation_length=int(
                            row.module_presentation_length
                        ),
                    )
                    for row in courses_df.itertuples(index=False)
                ],
                batch_size=BATCH_SIZE,
            )

            Student.objects.bulk_create(
                [
                    Student(
                        id_student=int(row.id_student),
                        gender=str(row.gender),
                        region=str(row.region),
                        highest_education=str(row.highest_education),
                        imd_band=(
                            "" if pd.isna(row.imd_band)
                            else str(row.imd_band)
                        ),
                        disability=str(row.disability),
                    )
                    for row in students_df.itertuples(index=False)
                ],
                batch_size=BATCH_SIZE,
            )

            student_ids = dict(
                Student.objects.values_list("id_student", "id")
            )
            course_ids = {
                (module, presentation): pk
                for pk, module, presentation in Course.objects.values_list(
                    "id", "code_module", "code_presentation"
                )
            }

            enrollments = []
            for row in info_df.itertuples(index=False):
                student_id = int(row.id_student)
                course_key_value = (
                    row.code_module,
                    row.code_presentation,
                )

                enrollments.append(
                    Enrollment(
                        student_id=student_ids[student_id],
                        course_id=course_ids[course_key_value],
                        age_band=str(row.age_band),
                        num_of_prev_attempts=int(
                            row.num_of_prev_attempts
                        ),
                        studied_credits=int(row.studied_credits),
                        final_result=str(row.final_result),
                        date_registration=optional_int(
                            row.date_registration
                        ),
                        date_unregistration=optional_int(
                            row.date_unregistration
                        ),
                    )
                )

            Enrollment.objects.bulk_create(
                enrollments,
                batch_size=BATCH_SIZE,
            )

            # Build a compact lookup table for assessment and interaction joins.
            enrollment_lookup = pd.DataFrame(
                Enrollment.objects.values_list(
                    "id",
                    "student__id_student",
                    "course__code_module",
                    "course__code_presentation",
                ),
                columns=[
                    "enrollment_id",
                    "id_student",
                    "code_module",
                    "code_presentation",
                ],
            )

            assessment_df = assessment_df.merge(
                enrollment_lookup,
                on=enrollment_key,
                how="left",
                validate="many_to_one",
                indicator=True,
            )

            missing_enrollment = assessment_df["_merge"] != "both"
            if missing_enrollment.any():
                raise CommandError(
                    f"{int(missing_enrollment.sum())} student assessment "
                    "records have no matching enrolment."
                )

            assessment_df = assessment_df.drop(columns="_merge")

            assessment_objects = []
            for row in assessment_df.itertuples(index=False):
                assessment_objects.append(
                    Assessment(
                        enrollment_id=int(row.enrollment_id),
                        id_assessment=int(row.id_assessment),
                        assessment_type=str(row.assessment_type),
                        assessment_date=optional_int(row.date),
                        weight=float(row.weight),
                        date_submitted=int(row.date_submitted),
                        is_banked=bool(row.is_banked),
                        score=optional_int(row.score) if pd.notna(row.score) else None,
                    )
                )

            Assessment.objects.bulk_create(
                assessment_objects,
                batch_size=BATCH_SIZE,
            )

        self.stdout.write(self.style.SUCCESS(
            "Courses, students, enrolments, and assessments imported."
        ))
        self.stdout.write(
            "Importing interactions in chunks. This may take a while..."
        )

        # Chunk transactions keep memory and transaction size bounded.
        # If interrupted, rerun with --replace to rebuild consistently.
        imported_interactions = 0

        for chunk in pd.read_csv(
            interactions_csv,
            chunksize=chunk_size,
        ):
            chunk = chunk.merge(
                enrollment_lookup,
                on=enrollment_key,
                how="left",
                validate="many_to_one",
                indicator=True,
            )

            unmatched = chunk["_merge"] != "both"
            if unmatched.any():
                examples = chunk.loc[
                    unmatched, enrollment_key
                ].head(5).to_dict("records")
                raise CommandError(
                    f"{int(unmatched.sum())} interaction rows have no "
                    f"matching enrolment. Examples: {examples}"
                )

            chunk = chunk.drop(columns="_merge")

            if (chunk["total_clicks"] < 0).any():
                raise CommandError(
                    "Interactions contain negative total_clicks."
                )

            interaction_objects = [
                Interaction(
                    enrollment_id=int(row.enrollment_id),
                    id_site=int(row.id_site),
                    date=int(row.date),
                    total_clicks=int(row.total_clicks),
                )
                for row in chunk.itertuples(index=False)
            ]

            with transaction.atomic():
                Interaction.objects.bulk_create(
                    interaction_objects,
                    batch_size=BATCH_SIZE,
                )

            imported_interactions += len(interaction_objects)
            self.stdout.write(
                f"Interactions imported: {imported_interactions:,}",
                ending="\r",
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("OULAD import completed."))
        self.stdout.write(
            f"Database counts — Courses: {Course.objects.count():,}; "
            f"Students: {Student.objects.count():,}; "
            f"Enrollments: {Enrollment.objects.count():,}; "
            f"Assessments: {Assessment.objects.count():,}; "
            f"Interactions: {Interaction.objects.count():,}."
        )
