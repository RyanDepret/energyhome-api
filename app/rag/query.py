import time

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.rag import embeddings, garde_fous, generation
from app.rag.documents import documents


# ── RAG ───────────────────────────────────────────────────────────────────────

def rag_query(question, top_k=3, locale="fr", modele="claude"):
    # La recherche et le prompt ne dépendent pas du modèle : seule la génération change
    index = embeddings.get_embeddings()

    question_embedding = embeddings.get_embedding(question)
    similarites = cosine_similarity([question_embedding], index)[0]
    indices_top = np.argsort(similarites)[::-1][:top_k]

    contexte = "\n\n".join([documents[idx] for idx in indices_top])
    sources = [
        {"extrait": documents[idx][:150] + "...", "score": float(similarites[idx])}
        for idx in indices_top
    ]

    langue = "anglais" if locale == "en" else "français"

    prompt = f"""Tu es l'assistant documentaire d'EnergyHome AI, spécialisé en rénovation énergétique.

{garde_fous.consignes(langue, locale)}
Sois clair et concis.

PASSAGES :
{contexte}

QUESTION : {question}

RÉPONSE :"""

    debut = time.perf_counter()
    resultat = generation.generer(modele, prompt)
    duree_ms = round((time.perf_counter() - debut) * 1000)

    # Filet de sécurité commun aux deux modèles : aucun montant absent des passages ne sort
    texte, _ = garde_fous.nettoyer_reponse(resultat.texte, contexte, locale)

    reponse = {"question": question, "reponse": texte, "sources": sources,
               "modele": modele, "duree_ms": duree_ms}
    if resultat.tokens is not None:
        reponse["tokens"] = resultat.tokens
    return reponse
