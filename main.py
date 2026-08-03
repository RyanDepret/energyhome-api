from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import joblib
import numpy as np

import models
import schemas
from database import engine, get_db
from rag import rag_query
from agent import agent_recommandations

# Chargement du modèle ML de prédiction DPE au démarrage
modele_ml = joblib.load("modele_dpe.pkl")

# Création des tables en base de données si elles n'existent pas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="EnergyHome AI API")

# Autorisation des requêtes depuis le front Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://energyhome-nextjs.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── ROUTES GÉNÉRALES ─────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "EnergyHome AI API"}

@app.get("/health")
def health():
    return {"status": "ok"}


# ── LOGEMENTS ────────────────────────────────────────────────────────────────

@app.get("/logements", response_model=List[schemas.LogementResponse])
def get_logements(db: Session = Depends(get_db)):
    return db.query(models.Logement).all()

@app.get("/logements/{logement_id}", response_model=schemas.LogementResponse)
def get_logement(logement_id: int, db: Session = Depends(get_db)):
    logement = db.query(models.Logement).filter(models.Logement.id == logement_id).first()
    if not logement:
        raise HTTPException(status_code=404, detail="Logement non trouvé")
    return logement

@app.get("/logements/classe/{classe}")
def get_logements_par_classe(classe: str, db: Session = Depends(get_db)):
    return db.query(models.Logement).filter(models.Logement.classe_dpe == classe).all()

@app.post("/logements", response_model=schemas.LogementResponse)
def create_logement(logement: schemas.LogementCreate, db: Session = Depends(get_db)):
    db_logement = models.Logement(**logement.model_dump())
    db.add(db_logement)
    db.commit()
    db.refresh(db_logement)
    return db_logement

@app.put("/logements/{logement_id}", response_model=schemas.LogementResponse)
def update_logement(logement_id: int, logement: schemas.LogementCreate, db: Session = Depends(get_db)):
    db_logement = db.query(models.Logement).filter(models.Logement.id == logement_id).first()
    if not db_logement:
        raise HTTPException(status_code=404, detail="Logement non trouvé")
    for key, value in logement.model_dump().items():
        setattr(db_logement, key, value)
    db.commit()
    db.refresh(db_logement)
    return db_logement

@app.delete("/logements/{logement_id}")
def delete_logement(logement_id: int, db: Session = Depends(get_db)):
    db_logement = db.query(models.Logement).filter(models.Logement.id == logement_id).first()
    if not db_logement:
        raise HTTPException(status_code=404, detail="Logement non trouvé")
    db.delete(db_logement)
    db.commit()
    return {"message": "Logement supprimé"}


# ── IA ────────────────────────────────────────────────────────────────────────

@app.post("/predict")
def predict_dpe(data: schemas.PredictionInput):
    # Prédiction de la classe DPE via le modèle Random Forest
    features = np.array([[
        data.surface,
        data.annee_construction,
        data.consommation_kwh,
        data.nb_pieces
    ]])
    prediction = modele_ml.predict(features)
    probabilites = modele_ml.predict_proba(features)
    confiance = float(probabilites.max()) * 100
    return {
        "classe_dpe": prediction[0],
        "confiance": f"{confiance:.1f}%",
        "surface": data.surface,
        "annee_construction": data.annee_construction
    }

@app.post("/chat")
def chat_assistant(data: schemas.ChatInput):
    # Réponse via le système RAG connecté à Mistral
    return rag_query(data.question)

@app.post("/agent")
def agent_dpe(data: schemas.AgentInput):
    # Génération de recommandations personnalisées par l'agent IA
    return agent_recommandations(
        classe_dpe=data.classe_dpe,
        surface=data.surface,
        annee_construction=data.annee_construction,
        consommation_kwh=data.consommation_kwh,
        nb_pieces=data.nb_pieces
    )


# ── CONTACT ───────────────────────────────────────────────────────────────────

@app.post("/contact")
def contact(data: schemas.ContactInput, db: Session = Depends(get_db)):
    # Sauvegarde du message de contact en base de données
    message = models.Contact(**data.model_dump())
    db.add(message)
    db.commit()
    return {"message": "Message envoyé avec succès"}