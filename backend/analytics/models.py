
from django.db import models


class Course(models.Model):
    code_module = models.CharField(max_length=3)
    code_presentation = models.CharField(max_length=5)
    module_presentation_length = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["code_module", "code_presentation"],
                name="unique_module_presentation",
            )
        ]

    def __str__(self):
        return f"{self.code_module} - {self.code_presentation}"


class Student(models.Model):
    # An anonymised student identifier from OULAD.
    id_student = models.PositiveBigIntegerField(unique=True)

    gender = models.CharField(max_length=1)
    region = models.CharField(max_length=100)
    highest_education = models.CharField(max_length=100)
    imd_band = models.CharField(max_length=20, blank=True, default="")
    disability = models.CharField(max_length=1)

    def __str__(self):
        return str(self.id_student)


class Enrollment(models.Model):
    # One student's enrolment in one course presentation.
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )

    age_band = models.CharField(max_length=20)
    num_of_prev_attempts = models.PositiveSmallIntegerField()
    studied_credits = models.PositiveSmallIntegerField()
    final_result = models.CharField(max_length=20)

    # These are relative day offsets, not calendar dates.
    date_registration = models.IntegerField(null=True, blank=True)
    date_unregistration = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrolment",
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.course}"


class Assessment(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    id_assessment = models.PositiveBigIntegerField()
    assessment_type = models.CharField(max_length=10)
    assessment_date = models.IntegerField(null=True, blank=True)
    weight = models.FloatField()
    date_submitted = models.IntegerField()
    is_banked = models.BooleanField()
    score = models.FloatField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "id_assessment"],
                name="unique_enrollment_assessment",
            )
        ]

    def __str__(self):
        return f"{self.enrollment} - Assessment {self.id_assessment}"


class Interaction(models.Model):
    # One aggregated resource interaction per enrolment and day.
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="interactions",
    )
    id_site = models.PositiveBigIntegerField()
    date = models.IntegerField()
    total_clicks = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "id_site", "date"],
                name="unique_enrollment_site_day",
            )
        ]

    def __str__(self):
        return (
            f"{self.enrollment} - Resource {self.id_site} "
            f"- Day {self.date}"
        )
