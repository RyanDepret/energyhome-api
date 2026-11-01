"""/chat avec modele=claude ou modele=mistral : génération simulée, aucun appel réseau ni crédit."""
import pytest
import requests

from app.core.config import settings
from app.rag import generation

ORIGINE = "http://localhost:3000"
QUESTION = {"question": "Quelles aides pour isoler ?"}


class FakeResponse:
    def __init__(self, status_code, corps=None):
        self.status_code = status_code
        self._corps = corps if corps is not None else {"message": "erreur simulée"}

    def json(self):
        return self._corps


def reponse_mistral(texte="Réponse de Mistral.", usage=True):
    corps = {"model": "mistral-small-latest",
             "choices": [{"index": 0, "message": {"role": "assistant", "content": texte}}]}
    if usage:
        corps["usage"] = {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
    return FakeResponse(200, corps)


@pytest.fixture
def faux_mistral(monkeypatch, mock_embedding):
    """Vraie generer_mistral, réponses HTTP simulées dans l'ordre ; les délais d'attente sont enregistrés."""
    monkeypatch.setattr(settings, "mistral_api_key", "cle-de-test")
    etat = {"reponses": [], "appels": [], "attentes": []}

    def fake_post(url, **kwargs):
        etat["appels"].append({"url": url, **kwargs})
        reponse = etat["reponses"].pop(0)
        if isinstance(reponse, Exception):
            raise reponse
        return reponse

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr("app.rag.generation.time.sleep", lambda s: etat["attentes"].append(s))
    return etat


# ── Choix du modèle ───────────────────────────────────────────────────────────

def test_chat_claude_par_defaut(client, mock_ai):
    corps = client.post("/chat", json=QUESTION).json()
    assert corps["modele"] == "claude"
    assert mock_ai.modeles == ["claude"]
    assert isinstance(corps["duree_ms"], int) and corps["duree_ms"] >= 0
    assert corps["tokens"] == {"entree": 10, "sortie": 5}


def test_chat_modele_claude(client, mock_ai):
    reponse = client.post("/chat", json={**QUESTION, "modele": "claude"})
    assert reponse.status_code == 200
    assert reponse.json()["modele"] == "claude"
    assert mock_ai.modeles == ["claude"]


def test_chat_modele_mistral(client, mock_ai):
    reponse = client.post("/chat", json={**QUESTION, "modele": "mistral"})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["modele"] == "mistral"
    assert len(corps["sources"]) == 3
    assert mock_ai.modeles == ["mistral"]


@pytest.mark.parametrize("modele", ["gpt", "Mistral", "", None])
def test_chat_modele_invalide_422(client, mock_ai, modele):
    reponse = client.post("/chat", json={**QUESTION, "modele": modele})
    assert reponse.status_code == 422
    assert mock_ai == []


def test_memes_sources_et_meme_prompt_pour_les_deux_modeles(client, mock_ai):
    claude = client.post("/chat", json={**QUESTION, "modele": "claude"}).json()
    mistral = client.post("/chat", json={**QUESTION, "modele": "mistral"}).json()
    assert claude["sources"] == mistral["sources"]
    # Même contexte et mêmes consignes : seule la génération change
    assert mock_ai.modeles == ["claude", "mistral"]
    assert mock_ai[0] == mock_ai[1]


# ── generer_mistral : appel HTTP, nouvelles tentatives, erreurs ───────────────

def test_mistral_meme_max_tokens_et_modele_configure(client, faux_mistral):
    faux_mistral["reponses"] = [reponse_mistral()]
    corps = client.post("/chat", json={**QUESTION, "modele": "mistral"}).json()
    assert corps["reponse"] == "Réponse de Mistral."
    assert corps["tokens"] == {"entree": 120, "sortie": 30}
    appel = faux_mistral["appels"][0]
    assert appel["url"] == generation.MISTRAL_CHAT_URL
    assert appel["json"]["model"] == settings.mistral_chat_model == "mistral-small-latest"
    assert appel["json"]["max_tokens"] == generation.MAX_TOKENS
    assert appel["timeout"] == settings.generation_timeout_s


def test_mistral_sans_usage_pas_de_tokens(client, faux_mistral):
    faux_mistral["reponses"] = [reponse_mistral(usage=False)]
    corps = client.post("/chat", json={**QUESTION, "modele": "mistral"}).json()
    assert "tokens" not in corps


def test_mistral_429_puis_succes(client, faux_mistral):
    faux_mistral["reponses"] = [FakeResponse(429), reponse_mistral()]
    reponse = client.post("/chat", json={**QUESTION, "modele": "mistral"})
    assert reponse.status_code == 200
    assert reponse.json()["reponse"] == "Réponse de Mistral."
    assert len(faux_mistral["appels"]) == 2
    assert faux_mistral["attentes"] == [1.0]


def test_mistral_indisponible_503_avec_cors(client, faux_mistral):
    # 1 appel + 2 nouvelles tentatives (délai croissant), puis 503 lisible avec l'en-tête CORS
    faux_mistral["reponses"] = [FakeResponse(503), FakeResponse(429), FakeResponse(502)]
    reponse = client.post("/chat", json={**QUESTION, "modele": "mistral"}, headers={"Origin": ORIGINE})
    assert reponse.status_code == 503
    assert reponse.headers["access-control-allow-origin"] == ORIGINE
    assert reponse.json()["code"] == "modele_indisponible"
    assert "Mistral est momentanément indisponible" in reponse.json()["detail"]
    assert len(faux_mistral["appels"]) == 3
    assert faux_mistral["attentes"] == [1.0, 2.0]


def test_mistral_erreur_4xx_pas_de_nouvelle_tentative(client, faux_mistral):
    faux_mistral["reponses"] = [FakeResponse(401)]
    reponse = client.post("/chat", json={**QUESTION, "modele": "mistral"})
    assert reponse.status_code == 503
    assert len(faux_mistral["appels"]) == 1


def test_mistral_delai_depasse_503(client, faux_mistral):
    faux_mistral["reponses"] = [requests.Timeout("trop long")]
    reponse = client.post("/chat", json={**QUESTION, "modele": "mistral"})
    assert reponse.status_code == 503
    assert "délai dépassé" in reponse.json()["detail"]


def test_cle_absente_503_message_clair(client, mock_embedding):
    # Aucune clé dans les tests : Claude et Mistral sont indisponibles, sans appel réseau
    for modele, nom in [("claude", "Claude"), ("mistral", "Mistral")]:
        reponse = client.post("/chat", json={**QUESTION, "modele": modele}, headers={"Origin": ORIGINE})
        assert reponse.status_code == 503
        assert reponse.headers["access-control-allow-origin"] == ORIGINE
        assert reponse.json()["detail"].startswith(f"{nom} est momentanément indisponible (clé API absente")
        assert "MISTRAL_API_KEY" not in reponse.json()["detail"]


# ── Recherche documentaire et erreurs inattendues ─────────────────────────────

def test_recherche_indisponible_503(client, monkeypatch):
    # Embedding de la question : délai maximal dépassé
    monkeypatch.setattr(settings, "mistral_api_key", "cle-de-test")
    appels = []

    def fake_post(url, **kwargs):
        appels.append(kwargs)
        raise requests.Timeout("trop long")

    monkeypatch.setattr(requests, "post", fake_post)
    reponse = client.post("/chat", json=QUESTION, headers={"Origin": ORIGINE})
    assert reponse.status_code == 503
    assert reponse.headers["access-control-allow-origin"] == ORIGINE
    assert reponse.json() == {
        "detail": "Recherche documentaire momentanément indisponible (délai dépassé), réessayez dans un instant.",
        "code": "recherche_indisponible",
    }
    assert appels[0]["timeout"] == settings.embedding_timeout_s


def test_recherche_erreur_http_503(client, monkeypatch):
    monkeypatch.setattr(settings, "mistral_api_key", "cle-de-test")
    monkeypatch.setattr(requests, "post", lambda url, **kw: FakeResponse(429))
    reponse = client.post("/chat", json=QUESTION)
    assert reponse.status_code == 503
    assert reponse.json()["code"] == "recherche_indisponible"


def test_erreur_inattendue_500_avec_cors(client, mock_embedding, monkeypatch):
    def plantage(prompt):
        raise ValueError("bug simulé")

    monkeypatch.setattr("app.rag.generation.generer_claude", plantage)
    reponse = client.post("/chat", json=QUESTION, headers={"Origin": ORIGINE})
    assert reponse.status_code == 500
    assert reponse.headers["access-control-allow-origin"] == ORIGINE
    assert reponse.json() == {"detail": "Erreur interne du serveur.", "code": "erreur_interne"}
