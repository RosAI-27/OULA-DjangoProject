from django.db.models import Sum
from analytics.models import Student, Course, Enrollment, Assessment, Interaction

print("Students:", Student.objects.count())
print("Courses:", Course.objects.count())
print("Enrollments:", Enrollment.objects.count())
print("Assessments:", Assessment.objects.count())
print("Interactions:", Interaction.objects.count())

print(
    "Assessments with missing scores:",
    Assessment.objects.filter(score__isnull=True).count()
)
print(
    "Enrollments without a student:",
    Enrollment.objects.filter(student__isnull=True).count()
)
print(
    "Enrollments without a course:",
    Enrollment.objects.filter(course__isnull=True).count()
)
print(
    "Assessments without an enrollment:",
    Assessment.objects.filter(enrollment__isnull=True).count()
)
print(
    "Interactions without an enrollment:",
    Interaction.objects.filter(enrollment__isnull=True).count()
)

total_clicks = Interaction.objects.aggregate(
    total=Sum("total_clicks")
)["total"]
print("Total recorded clicks:", total_clicks)

import pandas as pd
from pathlib import Path

csv_path = Path("data/processed/interactions.csv")

csv_total_clicks = 0

for chunk in pd.read_csv(csv_path, chunksize=100_000):
    csv_total_clicks += chunk["total_clicks"].sum()

print("CSV total clicks:", csv_total_clicks)
print("Database total clicks:", total_clicks)
print("Click totals match:", csv_total_clicks == total_clicks)