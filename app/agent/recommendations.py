import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json

from app.rag import embeddings, generation
from app.rag.documents import documents


def get_context(query, top_k=2):
    # Récupère les documents les plus pertinents pour une requête donnée
    index = embeddings.get_embeddings()
    q_emb = embeddings.get_embedding(query)
    sims = cosine_similarity([q_emb], index)[0]
    indices = np.argsort(sims)[::-1][:top_k]
    return "\n\n".join([documents[idx] for idx in indices])


def agent_recommandations(classe_dpe, surface, annee_construction,
                          type_batiment, type_chauffage, code_postal, locale="fr"):
    # Une seule requête large couvrant travaux, aides et réglementation
    # pour respecter la limite de 1 requête/seconde de l'API Mistral
    requete = ("loi climat résilience interdiction location classe G F E "
               "isolation pompe à chaleur MaPrimeRénov CEE aides financières travaux")
    contexte = get_context(requete, top_k=6)

    time.sleep(2)  # sécurité contre le rate limit d'1 req/s de Mistral

    langue = "anglais" if locale == "en" else "français"

    # Nuance selon le type de bâtiment : certains travaux nécessitent l'accord
    # de copropriété en appartement, alors qu'ils sont libres en maison
    contrainte_batiment = (
        "Ce logement est un appartement : les travaux touchant l'extérieur "
        "(isolation des murs, pompe à chaleur avec unité extérieure, panneaux solaires) "
        "nécessitent généralement l'accord de la copropriété. Mentionne cette nuance "
        "quand elle s'applique."
        if type_batiment == "appartement"
        else "Ce logement est une maison individuelle : le propriétaire peut engager "
        "librement les travaux extérieurs (isolation, pompe à chaleur, panneaux solaires) "
        "sans accord de copropriété."
    )

    prompt = f"""Tu es un assistant expert en rénovation énergétique.
Rédige TOUS les textes du JSON (titre, resume, detail, items) en {langue}.

Logement : Classe {classe_dpe}, {surface}m², {type_batiment}, construit en {annee_construction},
chauffage principal : {type_chauffage}, code postal {code_postal}.

{contrainte_batiment}

Utilise le code postal pour évaluer l'ensoleillement de la région et sa pertinence
pour l'installation de panneaux solaires si applicable.

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
{contexte}"""

    reponse = generation.generate_text(prompt)

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