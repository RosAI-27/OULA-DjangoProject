"""Outils de l'agent : chaque fonction interroge un endpoint de l'API du projet.

Les docstrings sont importantes : plus tard, c'est elles que l'agent lira
pour décider quel outil utiliser.
"""
import os

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")
DELAI_MAX_SECONDES = 120


def _appeler_api(chemin, params):
    """Calls an API endpoint and returns its JSON response or a readable error."""
    params = {k: v for k, v in params.items() if v not in ("", None)}
    try:
        reponse = requests.get(
            f"{API_BASE_URL}/{chemin}", params=params, timeout=DELAI_MAX_SECONDES
        )
        return reponse.json()
    except requests.exceptions.ConnectionError:
        return {"erreur": "Could not reach the API. Is the Django server running?"}
    except requests.exceptions.Timeout:
        return {"erreur": "The API request timed out."}
    except ValueError:
        return {"erreur": "The API response is not valid JSON."}


def get_reussite_par_cours(code_presentation: str = "") -> list | dict:
    """Returns enrollment counts, success rates, and withdrawal rates for each module (AAA, BBB, CCC, DDD, EEE, FFF, GGG). Optional parameter: code_presentation (2013B, 2013J, 2014B, or 2014J) to restrict the results to one presentation."""
    return _appeler_api(
        "stats/reussite-par-cours/", {"code_presentation": code_presentation}
    )


def get_engagement_par_semaine(code_module: str, code_presentation: str = "") -> list | dict:
    """Returns weekly platform engagement for a module: total clicks, number of active enrollments, and clicks per active enrollment. Required parameter: code_module (for example, AAA). Optional parameter: code_presentation (2013B, 2013J, 2014B, or 2014J)."""
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
    """Lists enrollments flagged by the course risk indicator, with an additive risk score, a level (eleve, moyen, faible), and plain-language reasons (low activity, low scores, recent inactivity, and so on). The maximum attainable score under the mutually exclusive rules is 100 points; it is not a probability. Required parameters: code_module and code_presentation. Optional parameters: jour (course cutoff day, default 60), niveau (eleve, moyen, or faible), and limite (maximum number of enrollments)."""
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