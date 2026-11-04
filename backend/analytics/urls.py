from django.urls import path

from .agent_views import AgentQuestionView
from .api_views import (
    EngagementParResultatView,
    EngagementParSemaineView,
    EtudiantsARisqueView,
    ReussiteParCoursView,
    ValidationRisqueView,
)
from .views import (
    AssessmentListAPIView,
    CourseEngagementAPIView,
    CourseListAPIView,
    CourseSuccessRateAPIView,
    EnrollmentListAPIView,
    StudentListAPIView,
)

urlpatterns = [
    # Consultation et analyses d'engagement
    path("courses/", CourseListAPIView.as_view(), name="course-list"),
    path("students/", StudentListAPIView.as_view(), name="student-list"),
    path("enrollments/", EnrollmentListAPIView.as_view(), name="enrollment-list"),
    path("assessments/", AssessmentListAPIView.as_view(), name="assessment-list"),
    path("analytics/engagement-by-course/", CourseEngagementAPIView.as_view(), name="course-engagement"),
    path("analytics/success-rate-by-course/", CourseSuccessRateAPIView.as_view(), name="course-success-rate"),
    # Statistiques du tableau de bord, score de risque et agent
    path("stats/reussite-par-cours/", ReussiteParCoursView.as_view()),
    path("stats/engagement-par-semaine/", EngagementParSemaineView.as_view()),
    path("stats/engagement-par-resultat/", EngagementParResultatView.as_view()),
    path("etudiants-a-risque/", EtudiantsARisqueView.as_view()),
    path("etudiants-a-risque/validation/", ValidationRisqueView.as_view()),
    path("agent/ask/", AgentQuestionView.as_view()),
]