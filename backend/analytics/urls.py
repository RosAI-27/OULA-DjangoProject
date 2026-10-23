from django.urls import path
from .agent_views import AgentQuestionView
from .api_views import (
    ReussiteParCoursView,
    EngagementParSemaineView,
    EtudiantsARisqueView,
)

urlpatterns = [
    path("stats/reussite-par-cours/", ReussiteParCoursView.as_view()),
    path("stats/engagement-par-semaine/", EngagementParSemaineView.as_view()),
    path("etudiants-a-risque/", EtudiantsARisqueView.as_view()),
    path("agent/ask/", AgentQuestionView.as_view()),
]