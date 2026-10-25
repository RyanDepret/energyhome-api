import pytest

from app.rag import embeddings, generation


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_routes_logements_supprimees(client):
    assert client.get("/logements").status_code == 404


def test_chat_avec_ia_simulee(client, mock_ai):
    reponse = client.post("/chat", json={"question": "Quelles aides pour isoler ?"})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["question"] == "Quelles aides pour isoler ?"
    assert len(corps["sources"]) == 3
    assert len(mock_ai) == 1


def test_agent_avec_ia_simulee(client, mock_ai):
    reponse = client.post("/agent", json={
        "classe_dpe": "F", "surface": 80, "annee_construction": 1976,
        "type_batiment": "appartement", "type_chauffage": "Gaz naturel", "code_postal": "13001",
    })
    assert reponse.status_code == 200
    recommandations = reponse.json()["recommandations"]
    assert recommandations["travaux"]["items"] == ["Isolation"]
    assert "copropriété" in mock_ai[0]


def test_contact(client):
    reponse = client.post("/contact", json={"nom": "Test", "email": "test@example.com", "message": "Bonjour"})
    assert reponse.status_code == 200


def test_sans_cle_api_erreur_claire_et_aucun_appel_reseau():
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        generation.generate_text("Bonjour")
    with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
        embeddings.get_embedding("Bonjour")
