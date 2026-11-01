import os
import tempfile

# Réglages forcés AVANT d'importer l'app : pas de clés API (les variables
# d'environnement priment sur un éventuel .env) et une base SQLite jetable
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["MISTRAL_API_KEY"] = ""
_db_dir = tempfile.mkdtemp(prefix="energyhome-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_db_dir, 'test.db')}"

import anthropic  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
import requests  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.rag import embeddings, generation  # noqa: E402

FAKE_AGENT_JSON = """{
  "situation": {"titre": "Situation actuelle", "icone": "🏠", "resume": "r", "detail": "d"},
  "travaux": {"titre": "Travaux prioritaires", "icone": "🔨", "resume": "r", "items": ["Isolation"]},
  "aides": {"titre": "Aides disponibles", "icone": "💶", "resume": "r", "items": ["MaPrimeRénov'"]}
}"""


def _network_forbidden(*args, **kwargs):
    raise RuntimeError("Appel réseau interdit pendant les tests")


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Garde-fou : tout appel HTTP réel ou client Anthropic fait échouer le test."""
    monkeypatch.setattr(requests, "post", _network_forbidden)
    monkeypatch.setattr(requests, "get", _network_forbidden)
    monkeypatch.setattr(anthropic, "Anthropic", _network_forbidden)


@pytest.fixture
def mock_embedding(monkeypatch):
    """Simule l'embedding Mistral de la question (recherche documentaire) : aucun appel réseau."""
    dimension = embeddings.get_embeddings().shape[1]
    monkeypatch.setattr("app.rag.embeddings.get_embedding", lambda text: np.ones(dimension))


@pytest.fixture
def mock_ai(monkeypatch, mock_embedding):
    """Simule la génération Claude et Mistral et l'embedding : aucun crédit consommé.

    Renvoie la liste des prompts reçus ; `mock_ai.modeles` donne le modèle appelé pour chacun.
    """
    prompts = PromptsRecus()

    def generateur(modele):
        def fake(prompt):
            prompts.append(prompt)
            prompts.modeles.append(modele)
            return generation.Generation(texte=FAKE_AGENT_JSON, tokens={"entree": 10, "sortie": 5})
        return fake

    monkeypatch.setattr("app.rag.generation.generer_claude", generateur("claude"))
    monkeypatch.setattr("app.rag.generation.generer_mistral", generateur("mistral"))
    monkeypatch.setattr("app.agent.recommendations.time.sleep", lambda s: None)
    return prompts


class PromptsRecus(list):
    def __init__(self):
        super().__init__()
        self.modeles = []


@pytest.fixture(scope="session")
def client():
    return TestClient(app)
