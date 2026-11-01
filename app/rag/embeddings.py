import logging
import os
import time
import pickle
import requests
import numpy as np

from app.core.config import settings
from app.core.erreurs import RechercheIndisponible
from app.rag.documents import documents


# ── EMBEDDINGS VIA MISTRAL (fonctionnait sans souci) ───────────────────────────

logger = logging.getLogger(__name__)


def get_api_key():
    if not settings.mistral_api_key:
        raise RechercheIndisponible("clé API absente côté serveur",
                                    "MISTRAL_API_KEY manquante : impossible de calculer un embedding.")
    return settings.mistral_api_key


def get_embedding(text):
    # Toute panne (clé absente, délai dépassé, erreur HTTP) devient RechercheIndisponible, convertie en 503
    url = "https://api.mistral.ai/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-embed",
        "input": [text]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=settings.embedding_timeout_s)
    except requests.Timeout as exc:
        logger.warning("Embedding Mistral : délai dépassé (%s s)", settings.embedding_timeout_s)
        raise RechercheIndisponible("délai dépassé", f"embedding Mistral : {exc!r}") from exc
    except requests.RequestException as exc:
        logger.warning("Embedding Mistral : connexion impossible (%r)", exc)
        raise RechercheIndisponible("connexion impossible", f"embedding Mistral : {exc!r}") from exc

    if response.status_code != 200:
        logger.warning("Embedding Mistral : HTTP %s", response.status_code)
        raise RechercheIndisponible("service saturé" if response.status_code == 429 else "erreur du fournisseur",
                                    f"embedding Mistral : HTTP {response.status_code}")
    try:
        return np.array(response.json()["data"][0]["embedding"])
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise RechercheIndisponible("réponse inattendue", f"embedding Mistral : {exc!r}") from exc


# ── INDEX DES EMBEDDINGS (calculé une fois, mis en cache sur disque) ──────────

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    chemin_cache = settings.embeddings_cache_path
    if os.path.exists(chemin_cache):
        with open(chemin_cache, "rb") as f:
            _embeddings = pickle.load(f)
        print(f"{len(documents)} documents chargés depuis le cache.")
        return _embeddings

    print("Calcul des embeddings de la base de connaissances...")
    resultats = []
    for doc in documents:
        resultats.append(get_embedding(doc))
        time.sleep(1.1)
    _embeddings = np.array(resultats)

    with open(chemin_cache, "wb") as f:
        pickle.dump(_embeddings, f)

    print(f"{len(documents)} documents indexés et sauvegardés dans le cache.")
    return _embeddings
