"""Agent conversationnel : un modèle de langage qui utilise les outils de tools.py.

Si un modèle est indisponible (surcharge, quota), l'agent essaie le suivant.
"""
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from .tools import (
    get_engagement_par_semaine,
    get_etudiants_a_risque,
    get_reussite_par_cours,
)

load_dotenv()

CONSIGNES = """You are an analytics assistant for a teaching team. Answer questions in English about student success and engagement in the Open University Learning Analytics Dataset (OULAD).

Règles :
- Use ONLY the data returned by your tools. Never invent figures.
- If the question is missing context (module or presentation), ask for it instead of guessing. Valid modules include AAA, BBB, CCC, DDD, EEE, FFF, and GGG; presentations include 2013B, 2013J, 2014B, and 2014J.
- When discussing students flagged by the risk indicator, explain the reasons returned by the tool.
- The risk score is a decision-support indicator, not a verdict. Remind users of this whenever discussing an individual student.
- If a tool returns an error or no data, state that clearly.
- Call as few tools as possible; one is usually enough. For risk-indicator queries, request no more than 10 students.
- Answer concisely and use a clear structure."""

OUTILS = [get_reussite_par_cours, get_engagement_par_semaine, get_etudiants_a_risque]


def _liste_modeles():
    """Modèle principal, puis modèles de secours (séparés par des virgules)."""
    principal = os.getenv("LLM_MODEL", "").strip()
    secours = os.getenv("LLM_MODELES_SECOURS", "")
    modeles = [principal] + [m.strip() for m in secours.split(",")]
    modeles = [m for m in modeles if m]
    if not modeles:
        raise RuntimeError(
            "La variable LLM_MODEL est absente du fichier .env "
            "(exemple : google_genai:NOM_DU_MODELE)."
        )
    return modeles


def _extraire_texte(contenu):
    """Selon le fournisseur, la réponse est du texte ou une liste de blocs."""
    if isinstance(contenu, str):
        return contenu
    morceaux = []
    for bloc in contenu:
        if isinstance(bloc, str):
            morceaux.append(bloc)
        elif isinstance(bloc, dict) and bloc.get("type") == "text":
            morceaux.append(bloc.get("text", ""))
    return "".join(morceaux)


_agents = {}


def _agent_pour(modele):
    if modele not in _agents:
        _agents[modele] = create_agent(
            model=init_chat_model(modele, timeout=30, max_retries=1),
            tools=OUTILS,
            system_prompt=CONSIGNES,
        )
    return _agents[modele]


def poser_question(question: str) -> str:
    """Accept an English question and return a text answer. Try configured models in order."""
    derniere_erreur = None
    for modele in _liste_modeles():
        try:
            resultat = _agent_pour(modele).invoke(
                {"messages": [{"role": "user", "content": question}]}
            )
            return _extraire_texte(resultat["messages"][-1].content)
        except Exception as e:
            print(f"Modèle {modele} indisponible : {e!r}")
            derniere_erreur = e
    raise derniere_erreur