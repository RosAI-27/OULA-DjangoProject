from django.db.models import Count
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .api_pagination import PaginationStandard
from .api_serializers import (
    AssessmentSerializer,
    CourseSerializer,
    EnrollmentSerializer,
    StudentSerializer,
)
from .models import Assessment, Course, Enrollment, Student


class FiltresParParametres:
    """Filtre la liste selon les paramètres de l'adresse (?param=valeur)."""

    filtres = {}  # nom du paramètre -> champ de la base

    def get_queryset(self):
        qs = super().get_queryset()
        for param, champ in self.filtres.items():
            valeur = self.request.query_params.get(param)
            if valeur:
                try:
                    qs = qs.filter(**{champ: valeur})
                except (ValueError, TypeError):
                    raise ValidationError({param: "Valeur invalide."})
        return qs


class CourseViewSet(FiltresParParametres, ReadOnlyModelViewSet):
    queryset = Course.objects.annotate(inscrits=Count("enrollments")).order_by(
        "code_module", "code_presentation"
    )
    serializer_class = CourseSerializer
    pagination_class = PaginationStandard
    permission_classes = [AllowAny]
    filtres = {
        "code_module": "code_module",
        "code_presentation": "code_presentation",
    }


class StudentViewSet(FiltresParParametres, ReadOnlyModelViewSet):
    queryset = Student.objects.order_by("id_student")
    serializer_class = StudentSerializer
    pagination_class = PaginationStandard
    permission_classes = [IsAuthenticated]
    lookup_field = "id_student"
    lookup_value_regex = "[0-9]+"
    filtres = {
        "region": "region",
        "gender": "gender",
        "highest_education": "highest_education",
    }


class EnrollmentViewSet(FiltresParParametres, ReadOnlyModelViewSet):
    queryset = Enrollment.objects.select_related("student", "course").order_by("id")
    serializer_class = EnrollmentSerializer
    pagination_class = PaginationStandard
    permission_classes = [IsAuthenticated]
    filtres = {
        "code_module": "course__code_module",
        "code_presentation": "course__code_presentation",
        "id_student": "student__id_student",
        "final_result": "final_result",
    }


class AssessmentViewSet(FiltresParParametres, ReadOnlyModelViewSet):
    queryset = Assessment.objects.select_related(
        "enrollment__student", "enrollment__course"
    ).order_by("id")
    serializer_class = AssessmentSerializer
    pagination_class = PaginationStandard
    permission_classes = [IsAuthenticated]
    filtres = {
        "code_module": "enrollment__course__code_module",
        "code_presentation": "enrollment__course__code_presentation",
        "id_student": "enrollment__student__id_student",
        "assessment_type": "assessment_type",
    }