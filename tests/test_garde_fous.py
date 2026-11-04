"""Garde-fou des montants : aucune réponse ne doit citer un montant ou un taux absent des passages."""
import pytest

from app.rag import garde_fous, generation

INSECABLE = chr(0xA0)
FINE = chr(0x202F)

CONTEXTE = """Une pompe à chaleur air-eau est un chauffage électrique au sens du DPE.
Elle peut être aidée par MaPrimeRénov' par geste selon vos revenus et par les CEE.
L'éco-PTZ finance jusqu'à 15 000 € pour une action et 50 000 € pour une performance globale.
Source : https://www.service-public.gouv.fr/particuliers/vosdroits/F35083 (vérifié le 2026-11-04)."""


def test_cas_reel_production_mistral():
    """Réponse réellement observée : montant inventé et fausse source."""
    texte = ("Pour une pompe à chaleur, vous pouvez bénéficier de MaPrimeRénov' jusqu'à 5 000 € "
             "pour les ménages modestes. Les CEE sont aussi possibles.\n\nSource : Contexte fourni")
    propre, retires = garde_fous.nettoyer_reponse(texte, CONTEXTE)
    assert "5 000" not in propre
    assert "Contexte fourni" not in propre
    assert "Les CEE sont aussi possibles." in propre
    assert propre.endswith(garde_fous.RENVOI["fr"])
    assert len(retires) == 2


@pytest.mark.parametrize("ecriture", [
    "5000 €", "5 000 €", f"5{INSECABLE}000 €", f"5{FINE}000€", "5.000 euros", "5 k€", "70 %", "45 pour cent",
])
def test_montants_inventes_detectes_quelle_que_soit_l_ecriture(ecriture):
    assert garde_fous.montants_non_sources(f"Jusqu'à {ecriture} d'aide.", CONTEXTE)


@pytest.mark.parametrize("ecriture", ["15 000 €", "15000 euros", f"50{INSECABLE}000 €", "15 k€"])
def test_montants_presents_dans_les_passages_conserves(ecriture):
    texte = f"L'éco-PTZ peut financer {ecriture}."
    propre, retires = garde_fous.nettoyer_reponse(texte, CONTEXTE)
    assert retires == []
    assert propre == texte


def test_source_avec_url_des_passages_conservee():
    texte = "Les CEE sont possibles.\nSource : https://www.service-public.gouv.fr/particuliers/vosdroits/F35083"
    propre, retires = garde_fous.nettoyer_reponse(texte, CONTEXTE)
    assert retires == []
    assert "F35083" in propre


def test_en_tete_sources_seul_conserve():
    """Vu en vérification réelle : Claude met « **Sources :** » puis les URL en liste."""
    texte = ("Les CEE sont possibles.\n\n**Sources :**\n"
             "- https://www.service-public.gouv.fr/particuliers/vosdroits/F35083")
    propre, retires = garde_fous.nettoyer_reponse(texte, CONTEXTE)
    assert retires == []
    assert "**Sources :**" in propre


def test_puce_avec_montant_invente_supprimee_entierement():
    texte = "Aides possibles :\n- MaPrimeRénov' : 4 000 €\n- CEE : selon les travaux"
    propre, _ = garde_fous.nettoyer_reponse(texte, CONTEXTE)
    assert "4 000" not in propre
    assert "- CEE : selon les travaux" in propre
    assert "\n- \n" not in propre


def test_renvoi_non_duplique():
    texte = f"Prime de 3 000 €. {garde_fous.RENVOI['fr']}"
    propre, _ = garde_fous.nettoyer_reponse(texte, CONTEXTE)
    assert propre.count("mesaides.france-renov.gouv.fr") == 1


def test_renvoi_en_anglais():
    propre, _ = garde_fous.nettoyer_reponse("Up to 5,000 € of aid.", CONTEXTE, locale="en")
    assert propre.endswith(garde_fous.RENVOI["en"])


def test_reponse_sans_montant_inchangee():
    texte = "Je n'ai pas cette information."
    assert garde_fous.nettoyer_reponse(texte, CONTEXTE) == (texte, [])


# ── Branchement dans /chat et /agent ─────────────────────────────────────────

@pytest.mark.parametrize("modele", ["claude", "mistral"])
def test_chat_retire_le_montant_invente_pour_les_deux_modeles(client, mock_embedding, monkeypatch, modele):
    prompts = []

    def fausse_generation(prompt):
        prompts.append(prompt)
        return generation.Generation(texte="MaPrimeRénov' donne 987 654 € pour une PAC. Source : Contexte fourni")

    monkeypatch.setattr(f"app.rag.generation.generer_{modele}", fausse_generation)
    reponse = client.post("/chat", json={"question": "Quelles aides pour une pompe à chaleur ?", "modele": modele})
    assert reponse.status_code == 200
    texte = reponse.json()["reponse"]
    assert "987" not in texte
    assert "Contexte fourni" not in texte
    assert "mesaides.france-renov.gouv.fr" in texte
    # Les règles sont bien dans le prompt
    assert "Ne donne jamais un montant" in prompts[0]
    assert "Je n'ai pas cette information" in prompts[0]
    assert garde_fous.RENVOI["fr"] in prompts[0]


def test_meme_consignes_pour_claude_et_mistral(client, mock_ai):
    question = {"question": "Quelles aides pour une pompe à chaleur ?"}
    client.post("/chat", json={**question, "modele": "claude"})
    client.post("/chat", json={**question, "modele": "mistral"})
    assert mock_ai.modeles == ["claude", "mistral"]
    assert mock_ai[0] == mock_ai[1]


def test_agent_retire_les_items_a_montant_invente(client, mock_embedding, monkeypatch):
    faux_json = """{
      "situation": {"titre": "Situation", "icone": "🏠", "resume": "Classe F.", "detail": "Location interdite en 2028."},
      "travaux": {"titre": "Travaux", "icone": "🔨", "resume": "r", "items": ["Isolation des combles : 4 321 €", "VMC"]},
      "aides": {"titre": "Aides", "icone": "💶", "resume": "r", "items": ["MaPrimeRénov' : 9 876 €", "CEE"]}
    }"""
    prompts = []
    monkeypatch.setattr("app.rag.generation.generate_text", lambda p: prompts.append(p) or faux_json)
    monkeypatch.setattr("app.agent.recommendations.time.sleep", lambda s: None)
    reponse = client.post("/agent", json={
        "classe_dpe": "F", "surface": 80, "annee_construction": 1976,
        "type_batiment": "maison", "type_chauffage": "Gaz naturel", "code_postal": "13001",
    })
    reco = reponse.json()["recommandations"]
    assert reco["travaux"]["items"] == ["VMC"]
    assert reco["aides"]["items"] == ["CEE", garde_fous.RENVOI["fr"]]
    assert "avec montant" not in prompts[0]
    assert "Ne donne jamais un montant" in prompts[0]
