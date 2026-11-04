"""Garde-fous appliqués à la réponse générée, identiques pour Claude et Mistral.

Les consignes du prompt ne suffisent pas : en production, Mistral Small a répondu
« MaPrimeRénov' jusqu'à 5 000 € » alors qu'aucun passage ne contenait ce montant.
Ici, toute phrase qui cite un montant (€) ou un pourcentage absent des passages est retirée,
et une mention « Source » qui ne renvoie à aucune URL des passages aussi.
"""
import logging
import re

logger = logging.getLogger(__name__)

RENVOI = {
    "fr": ("Montant selon votre situation : simulateur officiel Mes Aides Réno "
           "(mesaides.france-renov.gouv.fr) ou conseiller France Rénov' (0 808 800 700)."),
    "en": ("Amount depending on your situation: official Mes Aides Réno simulator "
           "(mesaides.france-renov.gouv.fr) or a France Rénov' advisor (0 808 800 700)."),
}

# Nombre : 5000, 5 000 (tout espace hors retour à la ligne, insécables compris, ou point
# comme séparateur de milliers), 1,1
_NOMBRE = r"\d{1,3}(?:(?:[^\S\n]|\.)\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?"


# Montant ou taux : nombre suivi d'une unité monétaire ou de pourcentage
_MONTANT = re.compile(rf"({_NOMBRE})\s*(k€|c€|€|euros?\b|eur\b|%|pour\s?cent\b)", re.IGNORECASE)
_TOUT_NOMBRE = re.compile(_NOMBRE)
_URL = re.compile(r"https?://[^\s)»\"']+|[\w-]+(?:\.[\w-]+)*\.gouv\.fr[^\s)»\"']*", re.IGNORECASE)
_SOURCE = re.compile(r"^\W*sources?\s*:", re.IGNORECASE)
_FIN_DE_PHRASE = re.compile(r"(?<=[.!?;])\s+")


def consignes(langue, locale="fr"):
    """Règles communes à /chat et /agent (même texte pour Claude et Mistral)."""
    renvoi = RENVOI.get(locale, RENVOI["fr"])
    return f"""RÈGLES À RESPECTER :
1. Réponds UNIQUEMENT à partir des passages fournis, sans aucune connaissance extérieure.
2. Ne donne jamais un montant, un taux, un plafond ou une date qui ne figure pas dans les passages.
   Si un montant n'y est pas, n'en donne aucun, même approximatif.
3. Si les passages ne contiennent pas la réponse, dis : « Je n'ai pas cette information. » N'invente rien.
4. Toute réponse qui parle d'aides financières se termine par cette phrase : « {renvoi} »
5. Pour citer une source, recopie l'URL de la ligne « Source : » du passage utilisé.
   N'écris jamais « Source : contexte fourni ».
6. Réponds en {langue}."""


def _normaliser(nombre, unite=""):
    """'5 000' -> '5000', '1.200' -> '1200', '1,1' -> '1,1', ('5', 'k€') -> '5000'."""
    n = re.sub(r"[^\S\n]", "", nombre)
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", n):
        n = n.replace(".", "")
    n = n.replace(".", ",")
    if unite.lower() == "k€" and "," not in n:
        n = str(int(n) * 1000)
    return n


def nombres_du_contexte(contexte):
    return {_normaliser(m.group(0)) for m in _TOUT_NOMBRE.finditer(contexte)}


def montants_non_sources(texte, contexte):
    """Montants et taux du texte absents des passages (liste des valeurs telles qu'écrites)."""
    connus = nombres_du_contexte(contexte)
    return [m.group(0) for m in _MONTANT.finditer(texte)
            if _normaliser(m.group(1), m.group(2)) not in connus]


def _urls(texte):
    return {u.rstrip(".,;").lower().removeprefix("https://").removeprefix("http://").removeprefix("www.")
            for u in _URL.findall(texte)}


def nettoyer_reponse(texte, contexte, locale="fr", ajouter_renvoi=True):
    """Retire les phrases à montant non sourcé et les fausses sources ; ajoute le renvoi si besoin.

    Renvoie (texte nettoyé, liste des éléments retirés).
    """
    urls_contexte = _urls(contexte)
    retires = []
    lignes = []
    for ligne in texte.split("\n"):
        phrases = []
        for phrase in _FIN_DE_PHRASE.split(ligne):
            # « Source : … » sans URL des passages (« Source : contexte fourni ») : fausse source
            # Un en-tête « **Sources :** » seul (URL sur les lignes suivantes) est conservé
            en_tete = _SOURCE.match(phrase) and not re.search(r"\w", phrase[_SOURCE.match(phrase).end():])
            fausse_source = (_SOURCE.match(phrase) and not en_tete
                             and not (_urls(phrase) & urls_contexte))
            if fausse_source or montants_non_sources(phrase, contexte):
                retires.append(phrase.strip())
            else:
                phrases.append(phrase)
        nouvelle = " ".join(phrases)
        # Ligne vidée par le filtre (puce, titre de liste…) : supprimée ; lignes vides d'origine conservées
        if ligne.strip() and not re.search(r"\w", nouvelle):
            continue
        lignes.append(nouvelle)

    resultat = re.sub(r"\n{3,}", "\n\n", "\n".join(lignes)).strip()
    if retires:
        logger.warning("Garde-fou : %d élément(s) non sourcé(s) retiré(s) de la réponse : %r", len(retires), retires)
        renvoi = RENVOI.get(locale, RENVOI["fr"])
        if ajouter_renvoi and "mesaides.france-renov.gouv.fr" not in resultat:
            resultat = f"{resultat}\n\n{renvoi}".strip()
    return resultat, retires
