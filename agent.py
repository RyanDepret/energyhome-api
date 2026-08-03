from rag import mistral_chat, get_embedding, get_embeddings, documents
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json

def get_context(query, top_k=2):
    embeddings = get_embeddings()
    q_emb = get_embedding(query)
    sims = cosine_similarity([q_emb], embeddings)[0]
    indices = np.argsort(sims)[::-1][:top_k]
    return "\n\n".join([documents[idx] for idx in indices])

def agent_recommandations(classe_dpe, surface, annee_construction, consommation_kwh, nb_pieces):
    contexte_travaux = get_context("isolation pompe chaleur rénovation travaux prioritaires")
    contexte_aides = get_context("MaPrimeRénov CEE éco-prêt aides financement")
    contexte_reglementaire = get_context(f"loi interdiction location classe {classe_dpe}")

    prompt = f"""Tu es un assistant expert en rénovation énergétique.

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
        # Nettoyer la réponse si elle contient des backticks
        reponse_clean = reponse.strip()
        if reponse_clean.startswith("```"):
            reponse_clean = reponse_clean.split("```")[1]
            if reponse_clean.startswith("json"):
                reponse_clean = reponse_clean[4:]
        data = json.loads(reponse_clean)
    except:
        # Fallback si le JSON est invalide
        data = {
            "situation": {"titre": "Situation", "icone": "🏠", "resume": f"Logement classé {classe_dpe}", "detail": reponse},
            "travaux": {"titre": "Travaux", "icone": "🔨", "resume": "Travaux recommandés", "items": []},
            "aides": {"titre": "Aides", "icone": "💶", "resume": "Aides disponibles", "items": []}
        }

    return {
        "classe_dpe": classe_dpe,
        "recommandations": data
    }