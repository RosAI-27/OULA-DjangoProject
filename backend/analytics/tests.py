from django.test import TestCase

# Create your tests here.
from rest_framework.test import APITestCase
from django.urls import reverse

from .models import Course, Student, Enrollment, Interaction


class AnalyticsAPITests(APITestCase):
    """Tests for the course engagement and success-rate endpoints."""

    @classmethod
    def setUpTestData(cls):
        # Create two course presentations.
        cls.course_a = Course.objects.create(
            code_module="AAA",
            code_presentation="2013J",
            module_presentation_length=268,
        )
        cls.course_b = Course.objects.create(
            code_module="BBB",
            code_presentation="2014B",
            module_presentation_length=240,
        )

        # Create three students.
        cls.student_1 = Student.objects.create(
            id_student=1001,
            gender="F",
            region="East Anglian Region",
            highest_education="HE Qualification",
            imd_band="10-20%",
            disability="N",
        )
        cls.student_2 = Student.objects.create(
            id_student=1002,
            gender="M",
            region="London",
            highest_education="A Level or Equivalent",
            imd_band="20-30%",
            disability="N",
        )
        cls.student_3 = Student.objects.create(
            id_student=1003,
            gender="F",
            region="Scotland",
            highest_education="Lower Than A Level",
            imd_band="30-40%",
            disability="Y",
        )

        # Course A: two passes, one fail and one withdrawal.
        cls.enrollment_pass = Enrollment.objects.create(
            student=cls.student_1,
            course=cls.course_a,
            age_band="0-35",
            num_of_prev_attempts=0,
            studied_credits=60,
            final_result="Pass",
        )
        cls.enrollment_distinction = Enrollment.objects.create(
            student=cls.student_2,
            course=cls.course_a,
            age_band="0-35",
            num_of_prev_attempts=0,
            studied_credits=60,
            final_result="Distinction",
        )
        cls.enrollment_fail = Enrollment.objects.create(
            student=cls.student_3,
            course=cls.course_a,
            age_band="35-55",
            num_of_prev_attempts=1,
            studied_credits=120,
            final_result="Fail",
        )

        # Course B has a withdrawal only: no completed enrollments.
        cls.enrollment_withdrawn = Enrollment.objects.create(
            student=cls.student_1,
            course=cls.course_b,
            age_band="0-35",
            num_of_prev_attempts=0,
            studied_credits=60,
            final_result="Withdrawn",
        )

        # Interactions: student 1 has two records in course A;
        # student 2 has one. This checks distinct-student counting.
        Interaction.objects.create(
            enrollment=cls.enrollment_pass,
            id_site=10,
            date=1,
            total_clicks=3,
        )
        Interaction.objects.create(
            enrollment=cls.enrollment_pass,
            id_site=11,
            date=2,
            total_clicks=5,
        )
        Interaction.objects.create(
            enrollment=cls.enrollment_distinction,
            id_site=10,
            date=1,
            total_clicks=7,
        )

        # One interaction in course B.
        Interaction.objects.create(
            enrollment=cls.enrollment_withdrawn,
            id_site=20,
            date=1,
            total_clicks=4,
        )

    def get_results(self, url, params=None):
        """Call a paginated endpoint and return its result list."""
        response = self.client.get(url, params or {})
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        return response.data["results"]

    def test_success_rate_counts_pass_and_distinction(self):
        results = self.get_results(
            reverse("course-success-rate")
        )
        result = next(
            item for item in results
            if item["code_module"] == "AAA"
        )

        self.assertEqual(result["total_enrollments"], 3)
        self.assertEqual(result["passed_enrollments"], 2)
        self.assertEqual(result["failed_enrollments"], 1)
        self.assertEqual(result["withdrawn_enrollments"], 0)
        self.assertEqual(result["completed_enrollments"], 3)
        self.assertEqual(result["success_rate"], 66.67)

    def test_withdrawals_are_excluded_from_success_rate_denominator(self):
        results = self.get_results(
            reverse("course-success-rate")
        )
        result = next(
            item for item in results
            if item["code_module"] == "BBB"
        )

        self.assertEqual(result["total_enrollments"], 1)
        self.assertEqual(result["passed_enrollments"], 0)
        self.assertEqual(result["failed_enrollments"], 0)
        self.assertEqual(result["withdrawn_enrollments"], 1)
        self.assertEqual(result["completed_enrollments"], 0)
        self.assertIsNone(result["success_rate"])

    def test_engagement_totals_and_distinct_students(self):
        results = self.get_results(
            reverse("course-engagement")
        )
        result = next(
            item for item in results
            if item["code_module"] == "AAA"
        )

        self.assertEqual(result["total_clicks"], 15)
        self.assertEqual(result["active_students"], 2)
        self.assertEqual(result["interaction_records"], 3)

    def test_engagement_can_be_filtered_by_module(self):
        results = self.get_results(
            reverse("course-engagement"),
            {"code_module": "BBB"},
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["code_module"], "BBB")
        self.assertEqual(results[0]["total_clicks"], 4)
        self.assertEqual(results[0]["active_students"], 1)
        self.assertEqual(results[0]["interaction_records"], 1)

    def test_engagement_can_be_filtered_by_presentation(self):
        results = self.get_results(
            reverse("course-engagement"),
            {"code_presentation": "2013J"},
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["code_module"], "AAA")
        self.assertEqual(results[0]["code_presentation"], "2013J")
