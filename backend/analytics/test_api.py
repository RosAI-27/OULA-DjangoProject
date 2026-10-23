from django.test import TestCase
from rest_framework.test import APIClient

from .models import Assessment, Course, Enrollment, Interaction, Student


def creer_etudiant(id_student):
    return Student.objects.create(
        id_student=id_student, gender="F", region="Test",
        highest_education="A Level or Equivalent", disability="N",
    )


def inscrire(student, course, resultat, desinscrit=None):
    return Enrollment.objects.create(
        student=student, course=course, age_band="0-35",
        num_of_prev_attempts=0, studied_credits=60,
        final_result=resultat, date_unregistration=desinscrit,
    )


class DonneesDeTest(TestCase):
    """Un cours AAA/2013J avec trois étudiants aux profils très différents."""

    def setUp(self):
        self.client = APIClient()
        self.cours = Course.objects.create(
            code_module="AAA", code_presentation="2013J",
            module_presentation_length=250,
        )

        # Étudiant A : actif récemment, bonnes notes, réussit
        self.a = inscrire(creer_etudiant(1), self.cours, "Pass")
        Interaction.objects.create(enrollment=self.a, id_site=1, date=55, total_clicks=500)
        Assessment.objects.create(
            enrollment=self.a, id_assessment=1, assessment_type="TMA",
            assessment_date=40, weight=10, date_submitted=40,
            is_banked=False, score=80,
        )

        # Étudiant B : aucune activité, aucune évaluation, abandonne
        self.b = inscrire(creer_etudiant(2), self.cours, "Withdrawn")

        # Étudiant C : désinscrit avant le jour 60, doit être exclu du score
        self.c = inscrire(creer_etudiant(3), self.cours, "Withdrawn", desinscrit=10)


class TestReussiteParCours(DonneesDeTest):
    def test_taux_calcules_sur_toutes_les_inscriptions(self):
        reponse = self.client.get("/api/stats/reussite-par-cours/")
        self.assertEqual(reponse.status_code, 200)
        aaa = reponse.json()[0]
        self.assertEqual(aaa["code_module"], "AAA")
        self.assertEqual(aaa["total"], 3)
        self.assertEqual(aaa["taux_reussite"], 33.3)  # 1 réussite sur 3
        self.assertEqual(aaa["taux_abandon"], 66.7)   # 2 abandons sur 3

    def test_filtre_sur_une_session_sans_donnees(self):
        reponse = self.client.get("/api/stats/reussite-par-cours/?code_presentation=2014J")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json(), [])


class TestEngagement(DonneesDeTest):
    def test_module_obligatoire(self):
        reponse = self.client.get("/api/stats/engagement-par-semaine/")
        self.assertEqual(reponse.status_code, 400)

    def test_clics_par_semaine(self):
        reponse = self.client.get("/api/stats/engagement-par-semaine/?code_module=AAA")
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        self.assertEqual(len(donnees), 1)
        self.assertEqual(donnees[0]["semaine"], 7)  # jour 55 -> semaine 7
        self.assertEqual(donnees[0]["total_clics"], 500)


class TestEtudiantsARisque(DonneesDeTest):
    URL = "/api/etudiants-a-risque/?code_module=AAA&code_presentation=2013J&jour=60"

    def test_parametres_obligatoires(self):
        reponse = self.client.get("/api/etudiants-a-risque/?code_module=AAA")
        self.assertEqual(reponse.status_code, 400)

    def test_jour_invalide(self):
        reponse = self.client.get(self.URL + "&jour=abc")
        self.assertEqual(reponse.status_code, 400)

    def test_etudiant_desinscrit_exclu(self):
        reponse = self.client.get(self.URL)
        ids = [e["id_student"] for e in reponse.json()["etudiants"]]
        self.assertNotIn(3, ids)

    def test_profils_classes_correctement(self):
        donnees = self.client.get(self.URL).json()
        niveaux = {e["id_student"]: e for e in donnees["etudiants"]}
        self.assertEqual(niveaux[1]["niveau"], "faible")
        self.assertEqual(niveaux[2]["niveau"], "eleve")
        # B : aucune activité (40) + inactif 14 jours (30) + aucune évaluation (15)
        self.assertEqual(niveaux[2]["score_risque"], 85)
        self.assertEqual(donnees["resume"], {"eleve": 1, "moyen": 0, "faible": 1})

    def test_tri_du_plus_au_moins_a_risque(self):
        scores = [e["score_risque"] for e in self.client.get(self.URL).json()["etudiants"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_filtre_par_niveau(self):
        donnees = self.client.get(self.URL + "&niveau=eleve").json()
        self.assertEqual([e["id_student"] for e in donnees["etudiants"]], [2])


class TestAgent(DonneesDeTest):
    def test_question_vide_refusee(self):
        reponse = self.client.post("/api/agent/ask/", {"question": "  "}, format="json")
        self.assertEqual(reponse.status_code, 400)

    def test_question_trop_longue_refusee(self):
        reponse = self.client.post("/api/agent/ask/", {"question": "x" * 1001}, format="json")
        self.assertEqual(reponse.status_code, 400)