import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.rag import embeddings, generation
from app.rag.documents import documents


# ── RAG ───────────────────────────────────────────────────────────────────────

def rag_query(question, top_k=3, locale="fr"):
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

    prompt = f"""Tu es un assistant expert en rénovation énergétique pour EnergyHome AI.

Réponds à la question en te basant UNIQUEMENT sur le contexte fourni ci-dessous.
Si l'information n'est pas dans le contexte, dis-le clairement.
Réponds en {langue}, de manière claire et concise.

CONTEXTE :
{contexte}

QUESTION : {question}

RÉPONSE :"""

    reponse = generation.generate_text(prompt)

    return {"question": question, "reponse": reponse, "sources": sources}
