from statistics import median
from django.db.models import Avg, Count, Sum, Q, IntegerField, ExpressionWrapper, F
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Assessment, Enrollment, Interaction


class ReussiteParCoursView(APIView):
    """Success and withdrawal rates by module, optionally filtered by presentation."""

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
    """Weekly course clicks for a required module and an optional presentation."""

    def get(self, request):
        module = request.query_params.get("code_module")
        presentation = request.query_params.get("code_presentation")

        if not module:
            return Response(
                {"erreur": "The code_module parameter is required, for example ?code_module=AAA"},
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
    """Calculates the risk score for each enrollment in a course at the selected cutoff day.

    Returns an unsorted list of dictionaries. The final outcome is included only
    for retrospective validation; it is not used to calculate the score.
    """
    # Course enrollments, excluding those already unregistered by the cutoff day
    inscriptions = list(
        Enrollment.objects.filter(
            course__code_module=module, course__code_presentation=presentation
        )
        .exclude(date_unregistration__lte=jour)
        .select_related("student")
    )

    # Total clicks from course day zero through the cutoff day
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

    # Enrollments with recorded activity during the 14 days before the cutoff
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

    # Mean non-missing assessment score submitted by the cutoff
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

    # Low-activity threshold: the lower-quartile course click count
    valeurs = sorted(clics.get(e.id, 0) for e in inscriptions)
    seuil_faible = valeurs[len(valeurs) // 4] if valeurs else 0

    etudiants = []
    for e in inscriptions:
        score = 0
        motifs = []

        c = clics.get(e.id, 0)
        if c == 0:
            score += 40
            motifs.append("No recorded platform clicks")
        elif c < seuil_faible:
            score += 25
            motifs.append(f"Low recorded activity ({c} clicks)")

        if e.id not in actifs_recents:
            score += 30
            motifs.append("No recorded activity in the previous 14 days")

        if e.id not in notes:
            score += 15
            motifs.append("No non-missing assessment score recorded by the cutoff")
        elif notes[e.id] < 40:
            score += 30
            motifs.append(f"Low mean assessment score ({notes[e.id]:.0f})")
        elif notes[e.id] < 55:
            score += 15
            motifs.append(f"Moderate mean assessment score ({notes[e.id]:.0f})")

        niveau = "eleve" if score >= 60 else "moyen" if score >= 30 else "faible"
        etudiants.append(
            {
                "id_student": e.student.id_student,
                "score_risque": score,
                "niveau": niveau,
                "total_clics": c,
                "moyenne_notes": round(notes[e.id], 1) if e.id in notes else None,
                "motifs": motifs,
                # Included only for retrospective validation; not used in the score calculation
                "resultat_final": e.final_result,
            }
        )
    return etudiants


class EtudiantsARisqueView(APIView):
    """Enrollments flagged by the risk indicator for one module presentation.

    Parameters: required code_module and code_presentation;
    jour (cutoff day, default 60); niveau (optional: eleve, moyen, faible);
    limite (maximum results, default 50).
    """

    def get(self, request):
        module = request.query_params.get("code_module")
        presentation = request.query_params.get("code_presentation")
        if not module or not presentation:
            return Response(
                {"erreur": "The code_module and code_presentation parameters are required, "
                           "par exemple ?code_module=AAA&code_presentation=2013J"},
                status=400,
            )

        try:
            jour = int(request.query_params.get("jour", 60))
            limite = int(request.query_params.get("limite", 50))
        except ValueError:
            return Response({"erreur": "jour and limite must be integers."}, status=400)

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
    """Compares risk levels with the observed final outcome.

    Parameters: required code_module and code_presentation; jour (cutoff day, default 60).
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
                {"erreur": "The code_module and code_presentation parameters are required."},
                status=400,
            )
        try:
            jour = int(request.query_params.get("jour", 60))
        except ValueError:
            return Response({"erreur": "jour must be an integer."}, status=400)

        etudiants = calculer_scores_risque(module, presentation, jour)
        if not etudiants:
            return Response({"erreur": "No data found for this module presentation."}, status=404)

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
    """Mean and median full-course click totals grouped by student final outcome.

    Parameters: required code_module; optional code_presentation.
    """

    ORDRE = ["Distinction", "Pass", "Fail", "Withdrawn"]

    def get(self, request):
        module = request.query_params.get("code_module")
        presentation = request.query_params.get("code_presentation")
        if not module:
            return Response(
                {"erreur": "The code_module parameter is required, for example ?code_module=AAA"},
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