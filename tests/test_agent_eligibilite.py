"""/agent : éligibilité calculée, documents joints d'office, règles imposées après génération (sans réseau)."""
import json

import pytest

from app.agent import eligibilite, recommendations
from app.rag import documents as base

# Cas réel signalé : maison de 100 m², 2013, électricité, classe A, 83600
MAISON_2013 = {"classe_dpe": "A", "surface": 100, "annee_construction": 2013,
               "type_batiment": "maison", "type_chauffage": "Électricité", "code_postal": "83600"}

# Réponse du modèle qui reproduit les 7 défauts observés en production
REPONSE_FAUTIVE = {
    "situation": {"titre": "Situation actuelle", "icone": "🏠",
                  "resume": "Maison performante classée A chauffée par une chaudière électrique.",
                  "detail": "En maison, vous pouvez réaliser les travaux sans accord préalable. "
                            "La TVA à 5,5 % s'applique à tous les travaux."},
    "travaux": {"titre": "Travaux prioritaires", "icone": "🔨", "resume": "Des travaux prioritaires s'imposent.",
                "items": ["Pompe à chaleur air-air (éligible MaPrimeRénov')", "Isolation des combles",
                          "Remplacement de la chaudière électrique"]},
    "aides": {"titre": "Aides disponibles", "icone": "💶", "resume": "MaPrimeRénov' finance vos travaux.",
              "items": ["MaPrimeRénov' pour l'isolation", "Mon Accompagnateur Rénov' gratuit",
                        "Prime CEE avant signature du devis"]},
}


# ── Calcul d'éligibilité ─────────────────────────────────────────────────────

def test_maison_2013_parcours_par_geste_limite_et_pas_d_ampleur():
    e = eligibilite.calculer("A", 2013, annee=2026)
    assert e.age == 13
    assert e.mpr_geste == "limite"           # PAC air-eau, géothermie, réseau de chaleur dès 2 ans
    assert e.mpr_ampleur == "non"
    assert e.gain_faible
    texte = " ".join(e.faits)
    assert "pompe à chaleur air-eau" in texte and "non éligible" in texte


@pytest.mark.parametrize("annee, attendu", [(1990, "oui"), (2010, "oui"), (2011, "a_verifier"),
                                            (2012, "limite"), (2023, "limite"), (2025, "non")])
def test_seuils_d_anciennete(annee, attendu):
    assert eligibilite.calculer("D", annee, annee=2026).mpr_geste == attendu


def test_deux_ans_pile_a_verifier():
    assert eligibilite.calculer("D", 2024, annee=2026).mpr_geste == "a_verifier"


@pytest.mark.parametrize("classe, ampleur", [("A", "non"), ("D", "non"), ("E", "oui"), ("F", "oui"), ("G", "oui")])
def test_renovation_d_ampleur_reservee_e_f_g(classe, ampleur):
    assert eligibilite.calculer(classe, 1975, annee=2026).mpr_ampleur == ampleur


def test_ampleur_exige_15_ans_sans_exception():
    assert eligibilite.calculer("G", 2015, annee=2026).mpr_ampleur == "non"


@pytest.mark.parametrize("classe, attendu", [("G", "interdite depuis le 1er janvier 2025"),
                                             ("F", "interdite à partir du 1er janvier 2028"),
                                             ("E", "interdite à partir du 1er janvier 2034"),
                                             ("C", "aucune interdiction")])
def test_location(classe, attendu):
    assert attendu in eligibilite.calculer(classe, 1975, annee=2026).location


# ── Documents joints d'office et recherche liée au logement ──────────────────

def test_chaque_sujet_designe_le_bon_document():
    for sujet, debut in base.DEBUTS.items():
        assert base.documents[base.indice(sujet)].startswith(debut)


def test_documents_joints_selon_le_logement(monkeypatch, mock_embedding):
    requetes = []
    vrai = recommendations.embeddings.get_embedding
    monkeypatch.setattr(recommendations.embeddings, "get_embedding", lambda q: requetes.append(q) or vrai(q))

    maison = recommendations.documents_du_logement("A", "Électricité", "maison", 2013)
    for sujet in ("mpr", "mpr_geste", "accompagnateur", "declaration", "tva", "coefficient"):
        assert base.indice(sujet) in maison
    assert base.indice("mpr_ampleur") not in maison and base.indice("location") not in maison

    appart = recommendations.documents_du_logement("F", "Gaz naturel", "appartement", 1975)
    assert base.indice("location") in appart and base.indice("mpr_ampleur") in appart

    assert len(requetes) == 2 and requetes[0] != requetes[1]   # requête propre à chaque logement
    assert len(set(maison)) == len(maison)


# ── /agent de bout en bout (génération simulée) ──────────────────────────────

@pytest.fixture
def agent_fautif(monkeypatch, mock_embedding):
    prompts = []
    monkeypatch.setattr("app.rag.generation.generate_text",
                        lambda p: prompts.append(p) or json.dumps(REPONSE_FAUTIVE, ensure_ascii=False))
    monkeypatch.setattr("app.agent.recommendations.time.sleep", lambda s: None)
    return prompts


def test_maison_2013_les_sept_defauts_sont_corriges(client, agent_fautif):
    corps = client.post("/agent", json=MAISON_2013).json()
    reco = corps["recommandations"]
    tout = json.dumps(reco, ensure_ascii=False).lower()

    # 1. MaPrimeRénov' : une seule ligne, calculée (pas d'isolation, PAC air-eau seulement)
    mpr = [a for a in reco["aides"]["items"] if "maprimerénov" in a.lower()]
    assert len(mpr) == 1 and "moins de 15 ans" in mpr[0] and "pompe à chaleur air-eau" in mpr[0]
    assert "maprimerénov' pour l'isolation" not in tout
    assert "rénovation d'ampleur" not in tout
    # 2. Pas de « sans accord préalable »
    assert "sans accord" not in tout
    # 3. Accompagnateur non présenté comme gratuit
    assert "accompagnateur rénov' gratuit" not in tout
    # 4. TVA non étendue à tous les travaux
    assert "tous les travaux" not in tout
    # 5. Aucune chaudière supposée
    assert "chaudière" not in tout
    # 6. La PAC air-air reste proposée, sans l'étiquette MaPrimeRénov'
    assert "Pompe à chaleur air-air" in reco["travaux"]["items"]
    # 7. Classe A : pas de travaux prioritaires, gain faible
    assert reco["travaux"]["titre"] == "Pistes d'amélioration"
    assert "faible" in reco["travaux"]["resume"] and "priorit" not in reco["travaux"]["resume"].lower()
    # Ce qui est juste est conservé
    assert "Prime CEE avant signature du devis" in reco["aides"]["items"]
    assert "Isolation des combles" in reco["travaux"]["items"]


def test_prompt_de_l_agent(client, agent_fautif):
    client.post("/agent", json=MAISON_2013)
    prompt = agent_fautif[0]
    assert "librement" not in prompt.replace("N'écris jamais que des travaux peuvent être faits librement", "")
    assert "ensoleillement" not in prompt
    assert "déclaration préalable" in prompt
    assert "« Électricité »" in prompt and "chaudière électrique" in prompt
    assert "moins de 15 ans" in prompt                     # faits calculés transmis
    assert "Pistes d'amélioration" in prompt
    # Les passages joints d'office sont bien dans le contexte
    for sujet in ("mpr", "accompagnateur", "declaration", "tva", "coefficient"):
        assert base.documents[base.indice(sujet)] in prompt


def test_sources_renvoyees(client, agent_fautif):
    corps = client.post("/agent", json=MAISON_2013).json()
    assert "https://www.service-public.gouv.fr/particuliers/vosdroits/F35083" in corps["sources"]
    assert "https://www.service-public.gouv.fr/particuliers/vosdroits/F17578" in corps["sources"]
    assert all(s.startswith("https://") for s in corps["sources"])
    assert len(corps["sources"]) == len(set(corps["sources"]))


def test_logement_ancien_classe_f_garde_l_ampleur(client, agent_fautif):
    corps = client.post("/agent", json={**MAISON_2013, "classe_dpe": "F", "annee_construction": 1975,
                                        "type_chauffage": "Gaz naturel", "type_batiment": "appartement"}).json()
    aides = corps["recommandations"]["aides"]["items"]
    assert any("rénovation d'ampleur : possible" in a for a in aides)
    assert corps["recommandations"]["travaux"]["titre"] != "Pistes d'amélioration"
    assert "vote de l'assemblée générale" in agent_fautif[0]
