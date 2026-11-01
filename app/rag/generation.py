import logging
import time
from dataclasses import dataclass

import anthropic
import requests

from app.core.config import settings
from app.core.erreurs import ModeleIndisponible

logger = logging.getLogger(__name__)

# Mêmes consignes pour les deux modèles : même prompt (un seul message utilisateur), même plafond de tokens
MAX_TOKENS = 1000
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"

# 1 appel + 2 nouvelles tentatives au maximum sur 429 et 5xx, avec un délai croissant (1 s puis 2 s)
NOUVELLES_TENTATIVES = 2
DELAI_INITIAL_S = 1.0


@dataclass
class Generation:
    texte: str
    # {"entree": ..., "sortie": ...} si le fournisseur renvoie l'usage, sinon None
    tokens: dict | None = None


# ── CLAUDE (SDK Anthropic) ────────────────────────────────────────────────────

def get_claude_client():
    if not settings.anthropic_api_key:
        raise ModeleIndisponible("claude", "clé API absente côté serveur",
                                 "ANTHROPIC_API_KEY manquante : impossible de générer du texte.")
    # Le SDK refait lui-même 2 tentatives avec délai croissant sur 429, 5xx et coupure réseau
    return anthropic.Anthropic(api_key=settings.anthropic_api_key,
                               timeout=settings.generation_timeout_s,
                               max_retries=NOUVELLES_TENTATIVES)


def generer_claude(prompt) -> Generation:
    client = get_claude_client()
    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}]
        )
    except anthropic.APITimeoutError as exc:
        logger.warning("Claude : délai dépassé")
        raise ModeleIndisponible("claude", "délai dépassé", repr(exc)) from exc
    except anthropic.APIStatusError as exc:
        logger.warning("Claude : HTTP %s", exc.status_code)
        sature = exc.status_code in (429, 529) or exc.status_code >= 500
        raise ModeleIndisponible("claude", "service saturé" if sature else "erreur du fournisseur",
                                 f"HTTP {exc.status_code}") from exc
    except anthropic.APIError as exc:
        logger.warning("Claude : %r", exc)
        raise ModeleIndisponible("claude", "connexion impossible", repr(exc)) from exc

    usage = getattr(message, "usage", None)
    tokens = ({"entree": usage.input_tokens, "sortie": usage.output_tokens}
              if usage is not None and usage.input_tokens is not None else None)
    return Generation(texte=message.content[0].text, tokens=tokens)


def generate_text(prompt):
    # Génère une réponse texte avec Claude Haiku (utilisé par /agent et par /chat avec modele=claude)
    return generer_claude(prompt).texte


# ── MISTRAL (HTTP direct, comme les embeddings) ───────────────────────────────

def _cle_mistral():
    if not settings.mistral_api_key:
        raise ModeleIndisponible("mistral", "clé API absente côté serveur",
                                 "MISTRAL_API_KEY manquante : impossible de générer du texte.")
    return settings.mistral_api_key


def _texte_mistral(contenu):
    # content est une chaîne ; certains modèles renvoient une liste de morceaux typés
    if isinstance(contenu, list):
        return "".join(m.get("text", "") for m in contenu if isinstance(m, dict))
    return contenu


def generer_mistral(prompt) -> Generation:
    headers = {"Authorization": f"Bearer {_cle_mistral()}", "Content-Type": "application/json"}
    payload = {
        "model": settings.mistral_chat_model,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }

    for tentative in range(NOUVELLES_TENTATIVES + 1):
        try:
            response = requests.post(MISTRAL_CHAT_URL, headers=headers, json=payload,
                                     timeout=settings.generation_timeout_s)
        except requests.Timeout as exc:
            logger.warning("Mistral : délai dépassé (%s s)", settings.generation_timeout_s)
            raise ModeleIndisponible("mistral", "délai dépassé", repr(exc)) from exc
        except requests.RequestException as exc:
            logger.warning("Mistral : connexion impossible (%r)", exc)
            raise ModeleIndisponible("mistral", "connexion impossible", repr(exc)) from exc

        statut = response.status_code
        if statut == 429 or statut >= 500:
            if tentative < NOUVELLES_TENTATIVES:
                delai = DELAI_INITIAL_S * 2 ** tentative
                logger.warning("Mistral : HTTP %s, nouvelle tentative dans %s s", statut, delai)
                time.sleep(delai)
                continue
            raise ModeleIndisponible("mistral", "service saturé",
                                     f"HTTP {statut} après {NOUVELLES_TENTATIVES} nouvelles tentatives")
        if statut != 200:
            logger.warning("Mistral : HTTP %s", statut)
            raise ModeleIndisponible("mistral", "erreur du fournisseur", f"HTTP {statut}")
        break

    try:
        corps = response.json()
        texte = _texte_mistral(corps["choices"][0]["message"]["content"])
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ModeleIndisponible("mistral", "réponse inattendue", repr(exc)) from exc

    usage = corps.get("usage") or {}
    tokens = ({"entree": usage["prompt_tokens"], "sortie": usage["completion_tokens"]}
              if "prompt_tokens" in usage and "completion_tokens" in usage else None)
    return Generation(texte=texte, tokens=tokens)


def generate_text_mistral(prompt):
    # Même usage que generate_text, avec le modèle Mistral configuré (mistral_chat_model)
    return generer_mistral(prompt).texte


def generer(modele, prompt) -> Generation:
    if modele == "mistral":
        return generer_mistral(prompt)
    return generer_claude(prompt)
