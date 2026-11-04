import hashlib
import json
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

# Modèle d'embedding : utilisé pour l'appel ET dans l'empreinte du cache
EMBEDDING_MODEL = "mistral-embed"


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
        "model": EMBEDDING_MODEL,
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
# Le cache enregistre une empreinte des documents et du modèle : si l'un des deux change,
# les vecteurs ne correspondent plus aux textes et sont recalculés (sinon la recherche
# renverrait de mauvais passages sans aucune erreur).

_embeddings = None


def empreinte_documents(docs=None, modele=None):
    """SHA-256 de la liste des documents et du nom du modèle d'embedding."""
    docs = documents if docs is None else docs
    modele = EMBEDDING_MODEL if modele is None else modele
    contenu = json.dumps({"modele": modele, "documents": list(docs)}, ensure_ascii=False)
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()


def _lire_cache(chemin_cache, empreinte):
    """Vecteurs du cache s'il correspond aux documents actuels, sinon None."""
    if not os.path.exists(chemin_cache):
        return None
    # pickle : fichier produit par l'API elle-même et commité dans le dépôt (même confiance que les modèles joblib)
    with open(chemin_cache, "rb") as f:
        cache = pickle.load(f)
    # Ancien format (tableau seul, sans empreinte) : impossible de savoir à quels textes il correspond
    if not isinstance(cache, dict) or cache.get("empreinte") != empreinte:
        logger.warning("Cache des embeddings périmé (documents ou modèle modifiés) : recalcul.")
        return None
    return cache["vecteurs"]


def calculer_embeddings(docs=None):
    """Calcule les embeddings de tous les documents (1 appel Mistral par document)."""
    docs = documents if docs is None else docs
    resultats = []
    for doc in docs:
        resultats.append(get_embedding(doc))
        time.sleep(1.1)  # limite d'1 requête par seconde de l'API Mistral
    return np.array(resultats)


def get_embeddings():
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    chemin_cache = settings.embeddings_cache_path
    empreinte = empreinte_documents()
    vecteurs = _lire_cache(chemin_cache, empreinte)
    if vecteurs is not None:
        _embeddings = vecteurs
        print(f"{len(documents)} documents chargés depuis le cache.")
        return _embeddings

    print("Calcul des embeddings de la base de connaissances...")
    vecteurs = calculer_embeddings()
    with open(chemin_cache, "wb") as f:
        pickle.dump({"empreinte": empreinte, "modele": EMBEDDING_MODEL, "vecteurs": vecteurs}, f)
    _embeddings = vecteurs

    print(f"{len(documents)} documents indexés et sauvegardés dans le cache.")
    return _embeddings
