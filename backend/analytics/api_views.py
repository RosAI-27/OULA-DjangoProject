from statistics import median
from django.db.models import Avg, Count, Sum, Q, IntegerField, ExpressionWrapper, F
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Assessment, Enrollment, Interaction


class ReussiteParCoursView(APIView):
    """Taux de réussite et d'abandon par module, filtrable par session."""

    def get(self, request):
        qs = Enrollment.objects.all()

        presentation = request.query_params.get("code_presentation")
        if presentation:
            qs = qs.filter(course__code_presentation=presentation)

        data = (
            qs.values("course__code_module")
            .annotate(
                total=Count("id"),
                reussis=Count("id", filter=Q(final_result__in=["Pass", "Distinction"])),
                abandons=Count("id", filter=Q(final_result="Withdrawn")),
            )
            .order_by("course__code_module")
        )

        result = [
            {
                "code_module": d["course__code_module"],
                "total": d["total"],
                "taux_reussite": round(100 * d["reussis"] / d["total"], 1),
                "taux_abandon": round(100 * d["abandons"] / d["total"], 1),
            }
            for d in data
        ]
        return Response(result)


class EngagementParSemaineView(APIView):
    """Clics par semaine de cours, pour un module (obligatoire) et une session (optionnelle)."""

    def get(self, request):
        module = request.query_params.get("code_module")
        presentation = request.query_params.get("code_presentation")

        if not module:
            return Response(
                {"erreur": "Le paramètre code_module est obligatoire, par exemple ?code_module=AAA"},
                status=400,
            )

        qs = Interaction.objects.filter(
            date__gte=0, enrollment__course__code_module=module
        )
        if presentation:
            qs = qs.filter(enrollment__course__code_presentation=presentation)

        data = (
            qs.annotate(
                semaine=ExpressionWrapper(F("date") / 7, output_field=IntegerField())
            )
            .values("semaine")
            .annotate(
                total_clics=Sum("total_clicks"),
                etudiants_actifs=Count("enrollment", distinct=True),
            )
            .order_by("semaine")
        )

        result = [
            {
                "semaine": d["semaine"],
                "total_clics": d["total_clics"],
                "etudiants_actifs": d["etudiants_actifs"],
                "clics_par_etudiant": round(d["total_clics"] / d["etudiants_actifs"], 1),
            }
            for d in data
        ]
        return Response(result)
def calculer_scores_risque(module, presentation, jour):
    """Calcule le score de risque de chaque étudiant d'un cours au jour de coupure.

    Retourne une liste de dictionnaires (non triée). Le résultat final est joint
    uniquement pour vérifier la pertinence du score : il n'entre pas dans le calcul.
    """
    # Inscriptions du cours, sans ceux déjà désinscrits avant le jour de coupure
    inscriptions = list(
        Enrollment.objects.filter(
            course__code_module=module, course__code_presentation=presentation
        )
        .exclude(date_unregistration__lte=jour)
        .select_related("student")
    )

    # Total des clics entre le début du cours et le jour de coupure
    clics = dict(
        Interaction.objects.filter(
            enrollment__course__code_module=module,
            enrollment__course__code_presentation=presentation,
            date__gte=0,
            date__lte=jour,
        )
        .values("enrollment_id")
        .annotate(t=Sum("total_clicks"))
        .values_list("enrollment_id", "t")
    )

    # Étudiants actifs pendant les 14 jours précédant la coupure
    actifs_recents = set(
        Interaction.objects.filter(
            enrollment__course__code_module=module,
            enrollment__course__code_presentation=presentation,
            date__gt=jour - 14,
            date__lte=jour,
        )
        .values_list("enrollment_id", flat=True)
        .distinct()
    )

    # Moyenne des notes rendues avant la coupure
    notes = {
        n["enrollment_id"]: n["moy"]
        for n in Assessment.objects.filter(
            enrollment__course__code_module=module,
            enrollment__course__code_presentation=presentation,
            date_submitted__lte=jour,
            score__isnull=False,
        )
        .values("enrollment_id")
        .annotate(moy=Avg("score"))
    }

    # Seuil de "faible activité" : le premier quart des étudiants du cours
    valeurs = sorted(clics.get(e.id, 0) for e in inscriptions)
    seuil_faible = valeurs[len(valeurs) // 4] if valeurs else 0

    etudiants = []
    for e in inscriptions:
        score = 0
        motifs = []

        c = clics.get(e.id, 0)
        if c == 0:
            score += 40
            motifs.append("aucune activité sur la plateforme")
        elif c < seuil_faible:
            score += 25
            motifs.append(f"activité faible ({c} clics)")

        if e.id not in actifs_recents:
            score += 30
            motifs.append("aucune activité sur les 14 derniers jours")

        if e.id not in notes:
            score += 15
            motifs.append("aucune évaluation rendue")
        elif notes[e.id] < 40:
            score += 30
            motifs.append(f"notes basses (moyenne {notes[e.id]:.0f})")
        elif notes[e.id] < 55:
            score += 15
            motifs.append(f"notes moyennes (moyenne {notes[e.id]:.0f})")

        niveau = "eleve" if score >= 60 else "moyen" if score >= 30 else "faible"
        etudiants.append(
            {
                "id_student": e.student.id_student,
                "score_risque": score,
                "niveau": niveau,
                "total_clics": c,
                "moyenne_notes": round(notes[e.id], 1) if e.id in notes else None,
                "motifs": motifs,
                # Uniquement pour vérifier la pertinence du score, pas utilisé dans le calcul
                "resultat_final": e.final_result,
            }
        )
    return etudiants


class EtudiantsARisqueView(APIView):
    """Étudiants à risque de décrochage pour un module et une session.

    Paramètres : code_module (obligatoire), code_presentation (obligatoire),
    jour (jour de coupure, défaut 60), niveau (optionnel : eleve, moyen, faible),
    limite (nombre max de résultats, défaut 50).
    """

    def get(self, request):
        module = request.query_params.get("code_module")
        presentation = request.query_params.get("code_presentation")
        if not module or not presentation:
            return Response(
                {"erreur": "Les paramètres code_module et code_presentation sont obligatoires, "
                           "par exemple ?code_module=AAA&code_presentation=2013J"},
                status=400,
            )

        try:
            jour = int(request.query_params.get("jour", 60))
            limite = int(request.query_params.get("limite", 50))
        except ValueError:
            return Response({"erreur": "jour et limite doivent être des nombres entiers."}, status=400)

        niveau_demande = request.query_params.get("niveau")
        etudiants = calculer_scores_risque(module, presentation, jour)

        resume = {"eleve": 0, "moyen": 0, "faible": 0}
        for et in etudiants:
            resume[et["niveau"]] += 1

        if niveau_demande:
            etudiants = [et for et in etudiants if et["niveau"] == niveau_demande]
        etudiants.sort(key=lambda et: et["score_risque"], reverse=True)

        return Response(
            {
                "parametres": {
                    "code_module": module,
                    "code_presentation": presentation,
                    "jour_coupure": jour,
                },
                "resume": resume,
                "etudiants": etudiants[:limite],
            }
        )


class ValidationRisqueView(APIView):
    """Compare le niveau de risque prédit au résultat final réel.

    Paramètres : code_module et code_presentation (obligatoires), jour (défaut 60).
    """

    ECHEC = ("Fail", "Withdrawn")
    REUSSITE = ("Pass", "Distinction")

    @classmethod
    def _stats(cls, resultats):
        n = len(resultats)
        if n == 0:
            return {"etudiants": 0, "pct_echec_ou_abandon": None, "pct_reussite": None}
        return {
            "etudiants": n,
            "pct_echec_ou_abandon": round(100 * sum(r in cls.ECHEC for r in resultats) / n, 1),
            "pct_reussite": round(100 * sum(r in cls.REUSSITE for r in resultats) / n, 1),
        }

    def get(self, request):
        module = request.query_params.get("code_module")
        presentation = request.query_params.get("code_presentation")
        if not module or not presentation:
            return Response(
                {"erreur": "Les paramètres code_module et code_presentation sont obligatoires."},
                status=400,
            )
        try:
            jour = int(request.query_params.get("jour", 60))
        except ValueError:
            return Response({"erreur": "jour doit être un nombre entier."}, status=400)

        etudiants = calculer_scores_risque(module, presentation, jour)
        if not etudiants:
            return Response({"erreur": "Aucune donnée pour ce module et cette session."}, status=404)

        groupes = {"eleve": [], "moyen": [], "faible": []}
        for e in etudiants:
            groupes[e["niveau"]].append(e["resultat_final"])

        return Response(
            {
                "parametres": {
                    "code_module": module,
                    "code_presentation": presentation,
                    "jour_coupure": jour,
                },
                "ensemble": self._stats([e["resultat_final"] for e in etudiants]),
                "niveaux": [
                    {"niveau": niveau, **self._stats(groupes[niveau])}
                    for niveau in ("eleve", "moyen", "faible")
                ],
            }
        )

class EngagementParResultatView(APIView):
    """Engagement moyen (clics sur tout le cours) selon le résultat final des étudiants.

    Paramètres : code_module (obligatoire), code_presentation (optionnel).
    """

    ORDRE = ["Distinction", "Pass", "Fail", "Withdrawn"]

    def get(self, request):
        module = request.query_params.get("code_module")
        presentation = request.query_params.get("code_presentation")
        if not module:
            return Response(
                {"erreur": "Le paramètre code_module est obligatoire, par exemple ?code_module=AAA"},
                status=400,
            )

        inscriptions = Enrollment.objects.filter(course__code_module=module)
        interactions = Interaction.objects.filter(enrollment__course__code_module=module)
        if presentation:
            inscriptions = inscriptions.filter(course__code_presentation=presentation)
            interactions = interactions.filter(enrollment__course__code_presentation=presentation)

        clics = dict(
            interactions.filter(date__gte=0)
            .values("enrollment_id")
            .annotate(t=Sum("total_clicks"))
            .values_list("enrollment_id", "t")
        )

        par_resultat = {}
        for enr_id, resultat in inscriptions.values_list("id", "final_result"):
            par_resultat.setdefault(resultat, []).append(clics.get(enr_id, 0))

        donnees = []
        for resultat in self.ORDRE:
            valeurs = par_resultat.get(resultat)
            if not valeurs:
                continue
            donnees.append(
                {
                    "resultat": resultat,
                    "inscrits": len(valeurs),
                    "clics_moyens": round(sum(valeurs) / len(valeurs), 1),
                    "clics_medians": round(median(valeurs), 1),
                }
            )
        return Response(donnees)     