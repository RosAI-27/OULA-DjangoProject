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

CONSIGNES = """Tu es un assistant d'analyse pour une équipe pédagogique. Tu réponds en français
à des questions sur la réussite et l'engagement des étudiants du jeu de données OULAD
(Open University).

Règles :
- Appuie-toi UNIQUEMENT sur les données renvoyées par tes outils. N'invente jamais de chiffre.
- Si la question manque d'information (module, session), demande-la au lieu de deviner.
  Les modules sont AAA, BBB, CCC, DDD, EEE, FFF, GGG ; les sessions sont 2013B, 2013J, 2014B, 2014J.
- Quand tu cites des étudiants à risque, explique les motifs fournis par l'outil.
- Le score de risque est un indicateur d'aide à la décision, pas un verdict : rappelle-le
  quand tu parles d'un étudiant en particulier.
- Si les outils renvoient une erreur ou aucune donnée, dis-le clairement.
- Appelle le moins d'outils possible : un seul suffit dans la plupart des cas.
  Pour les étudiants à risque, demande au plus 10 étudiants.
- Réponds de façon concise et structurée."""

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
    """Une question en français, une réponse en texte. Essaie chaque modèle à tour de rôle."""
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