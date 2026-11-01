import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import agent, chat, contact, predict
from app.core.config import settings
from app.core.erreurs import ServiceIndisponible
from app.db.database import engine
from app.db.models import Base  # importé via models pour enregistrer la table Contact

# Création des tables en base de données si elles n'existent pas
Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

app = FastAPI(title="EnergyHome AI API")


@app.exception_handler(ServiceIndisponible)
def service_indisponible(request: Request, exc: ServiceIndisponible):
    # Modèle ou recherche indisponible : 503 avec un message lisible (le détail technique reste dans les journaux)
    logger.warning("503 sur %s : %s", request.url.path, exc)
    return JSONResponse(status_code=503, content={"detail": exc.message_public, "code": exc.code})


# Gestionnaire global des erreurs inattendues. Déclaré AVANT le middleware CORS pour être enveloppé par lui :
# la 500 porte alors l'en-tête CORS et le navigateur affiche l'erreur au lieu de croire l'API injoignable.
# (Un gestionnaire @app.exception_handler(Exception) répondrait, lui, en dehors du middleware CORS.)
@app.middleware("http")
async def erreurs_inattendues(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Erreur inattendue sur %s", request.url.path)
        return JSONResponse(status_code=500,
                            content={"detail": "Erreur interne du serveur.", "code": "erreur_interne"})


# Autorisation des requêtes depuis le front Next.js (middleware le plus externe : s'applique à toutes les réponses)
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
