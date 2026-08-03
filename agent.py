from rag import mistral_chat, get_embedding, get_embeddings, documents
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json


def get_context(query, top_k=2):
    # Récupère les documents les plus pertinents pour une requête donnée
    embeddings = get_embeddings()
    q_emb = get_embedding(query)
    sims = cosine_similarity([q_emb], embeddings)[0]
    indices = np.argsort(sims)[::-1][:top_k]
    return "\n\n".join([documents[idx] for idx in indices])


def agent_recommandations(classe_dpe, surface, annee_construction,
                          consommation_kwh, nb_pieces, locale="fr"):
    # L'agent rassemble son contexte sur trois axes avant de générer le rapport
    contexte_travaux = get_context("isolation pompe chaleur rénovation travaux prioritaires")
    contexte_aides = get_context("MaPrimeRénov CEE éco-prêt aides financement")
    contexte_reglementaire = get_context(f"loi interdiction location classe {classe_dpe}")

    langue = "anglais" if locale == "en" else "français"

    prompt = f"""Tu es un assistant expert en rénovation énergétique.
Rédige TOUS les textes du JSON (titre, resume, detail, items) en {langue}.

Logement : Classe {classe_dpe}, {surface}m², construit en {annee_construction}, {consommation_kwh} kWh/an, {nb_pieces} pièces.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, avec exactement cette structure :

{{
  "situation": {{
    "titre": "Situation actuelle",
    "icone": "🏠",
    "resume": "1 phrase résumant la situation",
    "detail": "2 phrases sur les implications légales et financières"
  }},
  "travaux": {{
    "titre": "Travaux prioritaires",
    "icone": "🔨",
    "resume": "1 phrase sur l'urgence des travaux",
    "items": ["Travail 1 avec coût estimé", "Travail 2 avec coût estimé"]
  }},
  "aides": {{
    "titre": "Aides disponibles",
    "icone": "💶",
    "resume": "1 phrase sur le financement possible",
    "items": ["Aide 1 avec montant", "Aide 2 avec montant"]
  }}
}}

CONTEXTE :
{contexte_reglementaire}
{contexte_travaux}
{contexte_aides}"""

    reponse = mistral_chat(prompt)

    try:
        # Extraction du JSON, quelle que soit la forme de l'enrobage
        debut = reponse.find("{")
        fin = reponse.rfind("}")
        if debut == -1 or fin == -1:
            raise ValueError("Aucun JSON trouvé dans la réponse")
        data = json.loads(reponse[debut:fin + 1])
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
        "recommandations": data
    }