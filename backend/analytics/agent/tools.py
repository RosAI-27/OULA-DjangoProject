"""Outils de l'agent : chaque fonction interroge un endpoint de l'API du projet.

Les docstrings sont importantes : plus tard, c'est elles que l'agent lira
pour décider quel outil utiliser.
"""
import os

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")
DELAI_MAX_SECONDES = 120


def _appeler_api(chemin, params):
    """Appelle un endpoint et renvoie le JSON, ou un message d'erreur lisible."""
    params = {k: v for k, v in params.items() if v not in ("", None)}
    try:
        reponse = requests.get(
            f"{API_BASE_URL}/{chemin}", params=params, timeout=DELAI_MAX_SECONDES
        )
        return reponse.json()
    except requests.exceptions.ConnectionError:
        return {"erreur": "Impossible de joindre l'API. Le serveur Django est-il lancé ?"}
    except requests.exceptions.Timeout:
        return {"erreur": "L'API a mis trop de temps à répondre."}
    except ValueError:
        return {"erreur": "La réponse de l'API n'est pas du JSON valide."}


def get_reussite_par_cours(code_presentation: str = "") -> list | dict:
    """Donne, pour chaque module (AAA, BBB, CCC, DDD, EEE, FFF, GGG), le nombre
    d'inscrits, le taux de réussite et le taux d'abandon en pourcentage.
    Paramètre optionnel : code_presentation (2013B, 2013J, 2014B ou 2014J)
    pour se limiter à une session."""
    return _appeler_api(
        "stats/reussite-par-cours/", {"code_presentation": code_presentation}
    )


def get_engagement_par_semaine(code_module: str, code_presentation: str = "") -> list | dict:
    """Donne l'engagement sur la plateforme semaine par semaine pour un module :
    total de clics, nombre d'étudiants actifs et clics par étudiant actif.
    Paramètre obligatoire : code_module (par exemple AAA).
    Paramètre optionnel : code_presentation (2013B, 2013J, 2014B ou 2014J)."""
    return _appeler_api(
        "stats/engagement-par-semaine/",
        {"code_module": code_module, "code_presentation": code_presentation},
    )


def get_etudiants_a_risque(
    code_module: str,
    code_presentation: str,
    jour: int = 60,
    niveau: str = "",
    limite: int = 10,
) -> dict:
    """Liste les étudiants à risque de décrochage d'un cours, avec un score de
    risque de 0 à 100, un niveau (eleve, moyen, faible) et les motifs en clair
    (activité faible, notes basses, absence récente, etc.).
    Paramètres obligatoires : code_module et code_presentation.
    Paramètres optionnels : jour (jour de coupure du cours, 60 par défaut),
    niveau (eleve, moyen ou faible) et limite (nombre maximum d'étudiants)."""
    return _appeler_api(
        "etudiants-a-risque/",
        {
            "code_module": code_module,
            "code_presentation": code_presentation,
            "jour": jour,
            "niveau": niveau,
            "limite": limite,
        },
    )