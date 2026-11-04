from rest_framework.response import Response
from rest_framework.views import APIView

from .agent.agent import poser_question


class AgentQuestionView(APIView):
    """Accepts a question and returns a response."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        question = str(request.data.get("question", "")).strip()
        if not question:
            return Response({"erreur": "The question is empty."}, status=400)
        if len(question) > 1000:
            return Response({"erreur": "The question is too long (maximum 1,000 characters)."}, status=400)

        try:
            reponse = poser_question(question)
        except Exception as e:
            print("Agent error:", repr(e))  # visible in the server terminal
            return Response(
                {"erreur": "The assistant took too long to respond. Please try again or check your connection."},
                status=502,
            )
        return Response({"reponse": reponse})