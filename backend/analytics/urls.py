from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .agent_views import AgentQuestionView
from .api_viewsets import (
    AssessmentViewSet,
    CourseViewSet,
    EnrollmentViewSet,
    StudentViewSet,
)
from .api_views import (
    EngagementParResultatView,
    EngagementParSemaineView,
    EtudiantsARisqueView,
    ValidationRisqueView,
    ReussiteParCoursView,
)

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="course")
router.register("students", StudentViewSet, basename="student")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("assessments", AssessmentViewSet, basename="assessment")

urlpatterns = [
    path("stats/reussite-par-cours/", ReussiteParCoursView.as_view()),
    path("stats/engagement-par-semaine/", EngagementParSemaineView.as_view()),
    path("stats/engagement-par-resultat/", EngagementParResultatView.as_view()),
    path("etudiants-a-risque/", EtudiantsARisqueView.as_view()),
    path("etudiants-a-risque/validation/", ValidationRisqueView.as_view()),
    path("agent/ask/", AgentQuestionView.as_view()),
    path("", include(router.urls)),
]