from django.db.models import Count, Sum, F, Q
from django.shortcuts import render

# Create your views here.

from rest_framework import generics

from .models import Course, Student, Enrollment, Assessment, Interaction
from .serializers import CourseSerializer, StudentSerializer, EnrollmentSerializer, AssessmentSerializer, CourseEngagementSerializer, CourseSuccessRateSerializer


class CourseListAPIView(generics.ListAPIView):
    queryset = Course.objects.all().order_by(
        "code_module",
        "code_presentation",
    )
    serializer_class = CourseSerializer


class StudentListAPIView(generics.ListAPIView):
    serializer_class = StudentSerializer

    def get_queryset(self):
        queryset = Student.objects.all().order_by("id_student")

        gender = self.request.query_params.get("gender")
        region = self.request.query_params.get("region")


        if gender:
            queryset = queryset.filter(gender=gender)

        if region:
            queryset = queryset.filter(region__icontains=region)

        return queryset


class EnrollmentListAPIView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        queryset = Enrollment.objects.select_related(
            "student",
            "course",
        ).order_by(
            "course__code_module",
            "course__code_presentation",
            "student__id_student",
        )

        final_result = self.request.query_params.get("final_result")
        code_module = self.request.query_params.get("code_module")
        code_presentation = self.request.query_params.get(
            "code_presentation"
        )

        if final_result:
            queryset = queryset.filter(final_result=final_result)

        if code_module:
            queryset = queryset.filter(course__code_module=code_module)

        if code_presentation:
            queryset = queryset.filter(
                course__code_presentation=code_presentation
            )

        return queryset

class AssessmentListAPIView(generics.ListAPIView):
    serializer_class = AssessmentSerializer

    def get_queryset(self):
        queryset = Assessment.objects.select_related(
            "enrollment__student",
            "enrollment__course",
        ).order_by(
            "enrollment__course__code_module",
            "enrollment__course__code_presentation",
            "id_assessment",
            "enrollment__student__id_student",
        )

        assessment_type = self.request.query_params.get(
            "assessment_type"
        )
        code_module = self.request.query_params.get("code_module")
        code_presentation = self.request.query_params.get(
            "code_presentation"
        )

        if assessment_type:
            queryset = queryset.filter(
                assessment_type=assessment_type
            )

        if code_module:
            queryset = queryset.filter(
                enrollment__course__code_module=code_module
            )

        if code_presentation:
            queryset = queryset.filter(
                enrollment__course__code_presentation=code_presentation
            )

        return queryset


class CourseEngagementAPIView(generics.ListAPIView):
    serializer_class = CourseEngagementSerializer

    def get_queryset(self):
        queryset = Interaction.objects.all()

        code_module = self.request.query_params.get("code_module")
        code_presentation = self.request.query_params.get(
            "code_presentation"
        )

        if code_module:
            queryset = queryset.filter(
                enrollment__course__code_module=code_module
            )

        if code_presentation:
            queryset = queryset.filter(
                enrollment__course__code_presentation=code_presentation
            )

        return (
            queryset
            .values(
                code_module=F("enrollment__course__code_module"),
                code_presentation=F(
                    "enrollment__course__code_presentation"
                ),
            )
            .annotate(
                total_clicks=Sum("total_clicks"),
                active_students=Count(
                    "enrollment__student",
                    distinct=True,
                ),
                interaction_records=Count("id"),
            )
            .order_by("code_module", "code_presentation")
        )



class CourseSuccessRateAPIView(generics.ListAPIView):
    serializer_class = CourseSuccessRateSerializer

    def get_queryset(self):
        passed_results = ["Pass", "Distinction"]
        completed_results = ["Pass", "Distinction", "Fail"]

        return (
            Course.objects
            .annotate(
                total_enrollments=Count("enrollments"),
                passed_enrollments=Count(
                    "enrollments",
                    filter=Q(
                        enrollments__final_result__in=passed_results
                    ),
                ),
                failed_enrollments=Count(
                    "enrollments",
                    filter=Q(
                        enrollments__final_result="Fail"
                    ),
                ),
                withdrawn_enrollments=Count(
                    "enrollments",
                    filter=Q(
                        enrollments__final_result="Withdrawn"
                    ),
                ),
                completed_enrollments=Count(
                    "enrollments",
                    filter=Q(
                        enrollments__final_result__in=completed_results
                    ),
                ),
            )
            .values(
                "code_module",
                "code_presentation",
                "total_enrollments",
                "passed_enrollments",
                "failed_enrollments",
                "withdrawn_enrollments",
                "completed_enrollments",
            )
            .order_by("code_module", "code_presentation")
        )
