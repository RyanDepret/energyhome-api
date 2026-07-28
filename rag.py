import os
import requests
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

# Chargement de la clé API depuis .env
load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")

# Base de connaissances sur la rénovation énergétique
documents = [
    # ... garde tous tes documents existants
]

def get_embedding(text):
    # Génère un embedding via l'API Mistral
    url = "https://api.mistral.ai/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistral-embed",
        "input": [text]
    }
    response = requests.post(url, headers=headers, json=data)
    return np.array(response.json()["data"][0]["embedding"])

# Calcul des embeddings de la base de connaissances au démarrage
print("Chargement des embeddings...")
embeddings = np.array([get_embedding(doc) for doc in documents])
print("Embeddings chargés !")

def mistral_chat(prompt):
    # Appel au LLM Mistral pour générer une réponse
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistral-small-latest",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

def rag_query(question, top_k=3):
    # Retrieval — trouve les documents les plus pertinents
    question_embedding = get_embedding(question)
    similarites = cosine_similarity([question_embedding], embeddings)[0]
    indices_top = np.argsort(similarites)[::-1][:top_k]

    contexte = "\n\n".join([documents[idx] for idx in indices_top])
    sources = [{"extrait": documents[idx][:150] + "...", "score": float(similarites[idx])}
               for idx in indices_top]

    # Augmentation — construction du prompt avec contexte
    prompt = f"""Tu es un assistant expert en rénovation énergétique pour EnergyHome AI.

Réponds à la question en te basant UNIQUEMENT sur le contexte fourni ci-dessous.
Si l'information n'est pas dans le contexte, dis-le clairement.
Réponds en français, de manière claire et concise.

CONTEXTE :
{contexte}

QUESTION : {question}

RÉPONSE :"""

    # Generation — réponse du LLM
    reponse = mistral_chat(prompt)

    return {
        "question": question,
        "reponse": reponse,
        "sources": sources
    }