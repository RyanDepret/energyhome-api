from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent, chat, contact, predict
from app.core.config import settings
from app.db.database import engine
from app.db.models import Base  # importé via models pour enregistrer la table Contact

# Création des tables en base de données si elles n'existent pas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EnergyHome AI API")

# Autorisation des requêtes depuis le front Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router)
app.include_router(agent.router)
app.include_router(chat.router)
app.include_router(contact.router)


@app.get("/")
def root():
    return {"message": "EnergyHome AI API"}


@app.get("/health")
def health():
    return {"status": "ok"}
