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
modele_ml = joblib.load("modele_dpe_v2.pkl")
zones_climatiques = joblib.load("zones_climatiques.pkl")
colonnes_modele = joblib.load("colonnes_modele_v2.pkl")  # on charge aussi la structure des colonnes

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


# ── PRÉPARATION DES FEATURES POUR LE MODÈLE ────────────────────────────────────

def preparer_features(surface, annee_construction, type_batiment, type_chauffage, code_postal):
    # Étape 1 — déterminer la période de construction à partir de l'année
    if annee_construction < 1948:
        periode = "avant 1948"
    elif annee_construction < 1975:
        periode = "1948-1974"
    elif annee_construction < 2001:
        periode = "1975-2000"
    elif annee_construction < 2006:
        periode = "2001-2005"
    elif annee_construction < 2013:
        periode = "2006-2012"
    elif annee_construction <= 2021:
        periode = "2013-2021"
    else:
        periode = "après 2021"

    # Étape 2 — déterminer la zone climatique à partir du code postal
    departement = code_postal[:2]
    zone_climatique = zones_climatiques.get(departement, "H3")  # H3 par défaut si département inconnu

    # Étape 3 — créer un dictionnaire avec toutes les colonnes à 0
    features = {col: 0 for col in colonnes_modele}

    # Étape 4 — remplir la valeur numérique simple
    features['surface_habitable_logement'] = surface

    # Étape 5 — activer les bonnes colonnes One-Hot
    features[f"periode_construction_{periode}"] = 1
    features[f"type_batiment_{type_batiment}"] = 1
    features[f"type_energie_principale_chauffage_{type_chauffage}"] = 1
    features[f"zone_climatique_{zone_climatique}"] = 1

    # Étape 6 — transformer en tableau dans le bon ordre
    tableau = np.array([[features[col] for col in colonnes_modele]])

    return tableau


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
    departement = data.code_postal[:2]
    if departement not in zones_climatiques:
        raise HTTPException(
            status_code=400,
            detail="Ce simulateur est actuellement disponible uniquement pour la région PACA (04, 05, 06, 13, 83, 84)."
        )
    # Prédiction de la classe DPE via le modèle Random Forest v2
    features = preparer_features(
        surface=data.surface_habitable,
        annee_construction=data.annee_construction,
        type_batiment=data.type_batiment,
        type_chauffage=data.type_chauffage,
        code_postal=data.code_postal
    )
    prediction = modele_ml.predict(features)
    probabilites = modele_ml.predict_proba(features)
    confiance = float(probabilites.max()) * 100
    return {
        "classe_dpe": prediction[0],
        "confiance": f"{confiance:.1f}%",
        "surface": data.surface_habitable,
        "annee_construction": data.annee_construction
    }

@app.post("/chat")
def chat_assistant(data: schemas.ChatInput):
    return rag_query(data.question, locale=data.locale)

@app.post("/agent")
def agent_dpe(data: schemas.AgentInput):
    return agent_recommandations(
        classe_dpe=data.classe_dpe,
        surface=data.surface,
        annee_construction=data.annee_construction,
        type_batiment=data.type_batiment,
        type_chauffage=data.type_chauffage,
        code_postal=data.code_postal,
        locale=data.locale
    )


# ── CONTACT ───────────────────────────────────────────────────────────────────

@app.post("/contact")
def contact(data: schemas.ContactInput, db: Session = Depends(get_db)):
    # Sauvegarde du message de contact en base de données
    message = models.Contact(**data.model_dump())
    db.add(message)
    db.commit()
    return {"message": "Message envoyé avec succès"}