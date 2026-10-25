import os
import time
import pickle
import requests
import numpy as np

from app.core.config import settings
from app.rag.documents import documents


# ── EMBEDDINGS VIA MISTRAL (fonctionnait sans souci) ───────────────────────────

def get_api_key():
    if not settings.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY manquante : impossible de calculer un embedding.")
    return settings.mistral_api_key


def get_embedding(text):
    url = "https://api.mistral.ai/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-embed",
        "input": [text]
    }
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()

    if "data" not in result:
        raise RuntimeError(f"Erreur API Mistral (embeddings) : {result}")

    return np.array(result["data"][0]["embedding"])


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
