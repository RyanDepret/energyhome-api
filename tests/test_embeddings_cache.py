"""Cache des embeddings lié au contenu : embedding simulé, aucun appel réseau."""
import pickle

import numpy as np
import pytest

from app.core.config import settings
from app.rag import embeddings

DOCS = ["Premier document.", "Second document."]


@pytest.fixture
def cache_isole(monkeypatch, tmp_path):
    """Cache dans un dossier temporaire, documents de test, embedding simulé qui compte ses appels."""
    chemin = tmp_path / "embeddings.pkl"
    appels = []

    def faux_embedding(texte):
        appels.append(texte)
        return np.full(4, float(len(texte)))

    monkeypatch.setattr(settings, "embeddings_cache_path", chemin)
    monkeypatch.setattr(embeddings, "documents", list(DOCS))
    monkeypatch.setattr(embeddings, "get_embedding", faux_embedding)
    monkeypatch.setattr(embeddings.time, "sleep", lambda s: None)
    monkeypatch.setattr(embeddings, "_embeddings", None)
    return {"chemin": chemin, "appels": appels}


def _relancer(monkeypatch):
    # Simule un redémarrage de l'API : plus rien en mémoire, seul le fichier compte
    monkeypatch.setattr(embeddings, "_embeddings", None)
    return embeddings.get_embeddings()


def test_cache_valide_reutilise_sans_recalcul(monkeypatch, cache_isole):
    premiers = embeddings.get_embeddings()
    assert len(cache_isole["appels"]) == 2

    seconds = _relancer(monkeypatch)
    assert len(cache_isole["appels"]) == 2
    np.testing.assert_array_equal(premiers, seconds)


def test_documents_modifies_cache_invalide(monkeypatch, cache_isole):
    embeddings.get_embeddings()
    cache_isole["appels"].clear()

    monkeypatch.setattr(embeddings, "documents", ["Premier document corrigé.", "Second document."])
    vecteurs = _relancer(monkeypatch)

    assert cache_isole["appels"] == ["Premier document corrigé.", "Second document."]
    assert vecteurs.shape == (2, 4)
    with open(cache_isole["chemin"], "rb") as f:
        cache = pickle.load(f)
    assert cache["empreinte"] == embeddings.empreinte_documents(["Premier document corrigé.", "Second document."])


def test_modele_d_embedding_change_cache_invalide(monkeypatch, cache_isole):
    embeddings.get_embeddings()
    cache_isole["appels"].clear()

    monkeypatch.setattr(embeddings, "EMBEDDING_MODEL", "autre-modele")
    _relancer(monkeypatch)
    assert len(cache_isole["appels"]) == 2


def test_ancien_format_sans_empreinte_recalcule(monkeypatch, cache_isole):
    with open(cache_isole["chemin"], "wb") as f:
        pickle.dump(np.zeros((2, 4)), f)

    vecteurs = embeddings.get_embeddings()
    assert len(cache_isole["appels"]) == 2
    assert vecteurs.any()


def test_cache_commite_correspond_aux_documents():
    """Le .pkl embarqué dans l'image doit correspondre aux textes : sinon Cloud Run recalculerait au démarrage."""
    with open(settings.embeddings_cache_path, "rb") as f:
        cache = pickle.load(f)
    assert cache["empreinte"] == embeddings.empreinte_documents()
    assert len(cache["vecteurs"]) == len(embeddings.documents)
