from rest_framework.response import Response
from rest_framework.views import APIView

from .agent.agent import poser_question


class AgentQuestionView(APIView):
    """Reçoit {"question": "..."} et renvoie {"reponse": "..."}."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        question = str(request.data.get("question", "")).strip()
        if not question:
            return Response({"erreur": "La question est vide."}, status=400)
        if len(question) > 1000:
            return Response({"erreur": "La question est trop longue (1000 caractères maximum)."}, status=400)

        try:
            reponse = poser_question(question)
        except Exception as e:
            print("Erreur de l'agent :", repr(e))  # visible dans le terminal du serveur
            return Response(
                {"erreur": "L'assistant a mis trop de temps à répondre. Réessayez, ou vérifiez votre connexion."},
                status=502,
            )
        return Response({"reponse": reponse})