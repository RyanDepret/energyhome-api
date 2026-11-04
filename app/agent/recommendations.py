import json
import re
import time

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.agent import eligibilite
from app.rag import documents as base
from app.rag import embeddings, garde_fous, generation
from app.rag.documents import documents

# Nombre de passages ajoutés par la recherche, en plus des documents joints d'office
PASSAGES_RECHERCHES = 3

_MPR = re.compile(r"maprimer[ée]nov|r[ée]novation d'ampleur|major renovation", re.IGNORECASE)
# Formalités niées : faux pour l'ITE, les panneaux solaires et les fenêtres (déclaration préalable)
_SANS_FORMALITE = re.compile(r"sans (aucun )?accord|librement|sans (aucune )?(autorisation|formalit)"
                             r"|without (any )?(approval|permission)|freely", re.IGNORECASE)
_TVA_GENERALE = re.compile(r"(tva|vat).*(tous les travaux|ensemble des travaux|all (the )?work)"
                           r"|(tous les travaux|ensemble des travaux|all (the )?work).*(tva|vat)", re.IGNORECASE)
_ACCOMPAGNATEUR_GRATUIT = re.compile(r"accompagnateur.*(gratuit|free)|(gratuit|free).*accompagnateur",
                                     re.IGNORECASE)
_URL_SOURCE = re.compile(r"https?://[^\s;()]+")


def documents_du_logement(classe, type_chauffage, type_batiment, annee_construction):
    """Indices des passages : documents joints d'office selon le logement, puis recherche par similarité.

    Une seule requête d'embedding (limite d'1 requête par seconde de l'API Mistral).
    """
    classe = str(classe).strip().upper()
    sujets = ["mpr", "mpr_geste", "accompagnateur", "declaration", "tva"]
    if classe in ("E", "F", "G"):
        sujets += ["mpr_ampleur", "location"]
    if "électri" in type_chauffage.lower() or "electri" in type_chauffage.lower():
        sujets.append("coefficient")
    indices = [base.indice(s) for s in sujets]

    requete = (f"Logement {type_batiment} classé {classe} au DPE, chauffage : {type_chauffage}, "
               f"construit en {annee_construction}. Travaux de rénovation énergétique adaptés et aides.")
    index = embeddings.get_embeddings()
    sims = cosine_similarity([embeddings.get_embedding(requete)], index)[0]
    ajoutes = [int(i) for i in np.argsort(sims)[::-1] if int(i) not in indices][:PASSAGES_RECHERCHES]
    return indices + ajoutes


def sources_des_documents(indices):
    """URL officielles citées par les passages utilisés, sans doublon, dans l'ordre."""
    urls = []
    for i in indices:
        for url in _URL_SOURCE.findall(documents[i].rsplit("\n", 1)[-1]):
            if url not in urls:
                urls.append(url)
    return urls


def _retirer_phrases(texte, *motifs):
    phrases = [p for p in garde_fous._FIN_DE_PHRASE.split(texte) if not any(m.search(p) for m in motifs)]
    return " ".join(phrases).strip()


_PARENTHESE_MPR = re.compile(r"\s*\([^)]*(maprimer[ée]nov|r[ée]novation d'ampleur)[^)]*\)", re.IGNORECASE)
_MEMBRE_MPR = re.compile(r"\s*[,;:–—]\s*[^,;:–—.]*(maprimer[ée]nov|r[ée]novation d'ampleur)[^,;:–—.]*",
                         re.IGNORECASE)


def _retirer_mentions_mpr(texte):
    """« PAC air-eau (éligible MaPrimeRénov') » -> « PAC air-eau » : on garde le travail, pas l'aide."""
    texte = _PARENTHESE_MPR.sub("", texte)
    texte = _MEMBRE_MPR.sub("", texte)
    return _retirer_phrases(texte, _MPR)


def _imposer_regles(data, elig, type_chauffage, locale):
    """Corrige en code ce que le modèle ne doit pas décider : MaPrimeRénov', formalités, TVA, suppositions."""
    motifs = [_SANS_FORMALITE, _TVA_GENERALE, _ACCOMPAGNATEUR_GRATUIT]
    chauffage = type_chauffage.lower()
    if "chaudière" not in chauffage and "chaudiere" not in chauffage and "boiler" not in chauffage:
        # « Électricité » ne dit pas « chaudière électrique » : ne rien supposer
        motifs.append(re.compile(r"chaudi[èe]re|boiler", re.IGNORECASE))
    # L'éligibilité à MaPrimeRénov' n'est jamais rédigée par le modèle : la ligne calculée la remplace.
    # Aides : l'item entier part. Ailleurs : seule la mention part, le travail proposé reste.
    def nettoyer(texte, cle):
        texte = _retirer_phrases(texte, *motifs)
        return _retirer_phrases(texte, _MPR) if cle == "aides" else _retirer_mentions_mpr(texte)

    for cle, section in data.items():
        if not isinstance(section, dict):
            continue
        for champ in ("resume", "detail"):
            if isinstance(section.get(champ), str):
                section[champ] = nettoyer(section[champ], cle)
        if isinstance(section.get("items"), list):
            items = []
            for item in section["items"]:
                if not isinstance(item, str):
                    continue
                propre = nettoyer(item, cle)
                if re.search(r"\w", propre):
                    items.append(propre)
            section["items"] = items

    aides = data.get("aides")
    if isinstance(aides, dict):
        aides["items"] = eligibilite.item_maprimerenov(elig, locale) + aides.get("items", [])

    travaux = data.get("travaux")
    if isinstance(travaux, dict) and elig.gain_faible:
        travaux["titre"] = "Improvement options" if locale == "en" else "Pistes d'amélioration"
        travaux["resume"] = (
            f"Home rated {elig.classe}: already efficient, the expected gain from work is small."
            if locale == "en" else
            f"Logement classé {elig.classe} : déjà performant, le gain attendu de travaux est faible.")
    return data


def _filtrer_montants(data, contexte, locale):
    """Même garde-fou que /chat : aucun montant ni taux absent du contexte dans les textes du JSON."""
    retire = False
    for section in data.values():
        if not isinstance(section, dict):
            continue
        for cle in ("resume", "detail"):
            if isinstance(section.get(cle), str):
                section[cle], retires = garde_fous.nettoyer_reponse(section[cle], contexte, locale,
                                                                     ajouter_renvoi=False)
                retire = retire or bool(retires)
        if isinstance(section.get("items"), list):
            items = []
            for item in section["items"]:
                if isinstance(item, str) and garde_fous.montants_non_sources(item, contexte):
                    retire = True
                else:
                    items.append(item)
            section["items"] = items
    aides = data.get("aides")
    if retire and isinstance(aides, dict) and isinstance(aides.get("items"), list):
        aides["items"].append(garde_fous.RENVOI.get(locale, garde_fous.RENVOI["fr"]))
    return data


def _consignes_agent(type_batiment, type_chauffage, elig):
    if type_batiment == "appartement":
        formalites = ("Ce logement est un appartement : les travaux sur les parties communes ou l'extérieur "
                      "(façade, toiture, unité extérieure) demandent un vote de l'assemblée générale de "
                      "copropriété, et ceux qui modifient l'aspect extérieur peuvent exiger une déclaration "
                      "préalable en mairie.")
    else:
        formalites = ("Ce logement est une maison individuelle : il n'y a pas de copropriété, mais les travaux "
                      "qui modifient l'aspect extérieur (isolation par l'extérieur, panneaux solaires, fenêtres) "
                      "peuvent exiger une déclaration préalable en mairie. N'écris jamais que des travaux "
                      "peuvent être faits librement ou sans formalité.")
    faits = "\n".join(f"- {f}" for f in elig.faits)
    prioritaire = ("Le logement est classé A ou B : n'emploie pas le mot « prioritaire », présente seulement des "
                   "pistes d'amélioration et dis que le gain attendu est faible."
                   if elig.gain_faible else
                   "Classe les travaux du plus utile au moins utile pour ce logement, sans inventer de coût.")
    return f"""FAITS CALCULÉS POUR CE LOGEMENT (exacts, ne les contredis jamais) :
{faits}

RÈGLES PROPRES À L'AGENT :
- Le chauffage saisi est exactement « {type_chauffage} ». Ne suppose aucun équipement qui n'est pas indiqué
  (par exemple, « électricité » ne veut pas dire « chaudière électrique »).
- N'écris rien sur MaPrimeRénov' ni sur la rénovation d'ampleur : la ligne correspondante est ajoutée
  automatiquement à partir des faits calculés.
- {formalites}
- Un taux de TVA ne s'applique qu'aux travaux énumérés dans le passage sur la TVA, jamais à « tous les travaux ».
- N'écris « gratuit » que si un passage le dit pour ce service précis : le conseiller France Rénov' est
  gratuit, Mon Accompagnateur Rénov' est payant (pris en charge selon les revenus).
- Si tu proposes une pompe à chaleur air-air, précise qu'elle ne figure pas dans le parcours par geste.
- {prioritaire}"""


def agent_recommandations(classe_dpe, surface, annee_construction,
                          type_batiment, type_chauffage, code_postal, locale="fr"):
    elig = eligibilite.calculer(classe_dpe, annee_construction)
    indices = documents_du_logement(classe_dpe, type_chauffage, type_batiment, annee_construction)
    contexte = "\n\n".join(documents[i] for i in indices)

    time.sleep(2)  # sécurité contre le rate limit d'1 req/s de Mistral

    langue = "anglais" if locale == "en" else "français"
    titre_travaux = "Pistes d'amélioration" if elig.gain_faible else "Travaux recommandés"

    prompt = f"""Tu es un assistant expert en rénovation énergétique.
Rédige TOUS les textes du JSON (titre, resume, detail, items) en {langue}.

{garde_fous.consignes(langue, locale)}

Logement : classe {classe_dpe}, {surface} m², {type_batiment}, construit en {annee_construction},
chauffage principal : {type_chauffage}, code postal {code_postal}.

{_consignes_agent(type_batiment, type_chauffage, elig)}

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, avec exactement cette structure :

{{
  "situation": {{
    "titre": "Situation actuelle",
    "icone": "🏠",
    "resume": "1 phrase résumant la situation",
    "detail": "2 phrases sur les obligations (location, vente) qui s'appliquent à ce logement"
  }},
  "travaux": {{
    "titre": "{titre_travaux}",
    "icone": "🔨",
    "resume": "1 phrase",
    "items": ["Travail 1 (coût seulement s'il figure dans le contexte)", "Travail 2"]
  }},
  "aides": {{
    "titre": "Aides disponibles",
    "icone": "💶",
    "resume": "1 phrase sur le financement possible",
    "items": ["Aide 1 (montant seulement s'il figure dans le contexte)", "Aide 2"]
  }}
}}

CONTEXTE :
{contexte}"""

    reponse = generation.generate_text(prompt)

    try:
        # Extraction du JSON, quelle que soit la forme de l'enrobage
        debut = reponse.find("{")
        fin = reponse.rfind("}")
        if debut == -1 or fin == -1:
            raise ValueError("Aucun JSON trouvé dans la réponse")
        data = json.loads(reponse[debut:fin + 1])
        data = _imposer_regles(data, elig, type_chauffage, locale)
        data = _filtrer_montants(data, contexte, locale)
    except Exception:
        # Fallback si le JSON est invalide ou tronqué
        indisponible = "Analysis unavailable" if locale == "en" else "Analyse indisponible"
        message = ("Recommendations could not be generated. Please try again."
                   if locale == "en"
                   else "Les recommandations n'ont pas pu être générées. Veuillez réessayer.")
        data = {
            "situation": {
                "titre": "Situation",
                "icone": "🏠",
                "resume": f"Classe {classe_dpe}",
                "detail": message
            },
            "travaux": {"titre": "Travaux", "icone": "🔨", "resume": indisponible, "items": []},
            "aides": {"titre": "Aides", "icone": "💶", "resume": indisponible, "items": []}
        }

    return {
        "classe_dpe": classe_dpe,
        "recommandations": data,
        # Documents de référence réellement transmis au modèle (le site annonce « documents de référence »)
        "sources": sources_des_documents(indices),
    }
