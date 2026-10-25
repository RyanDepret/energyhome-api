from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Racine du dépôt : les chemins des artefacts sont calculés à partir d'ici,
# pour ne pas dépendre du dossier depuis lequel on lance l'API
BASE_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = BASE_DIR / "artifacts"


class Settings(BaseSettings):
    """Réglages de l'API, lus depuis les variables d'environnement ou un fichier .env facultatif."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Clés API facultatives : l'API démarre sans elles, l'erreur n'arrive qu'à l'appel réel
    anthropic_api_key: str | None = None
    mistral_api_key: str | None = None

    # Origines autorisées pour le front Next.js
    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://energyhome-nextjs.vercel.app",
    ]

    # SQLite en local, PostgreSQL en production via variable d'environnement
    database_url: str = "sqlite:///./energyhome.db"

    # Chemins des artefacts du modèle et du RAG
    model_path: Path = ARTIFACTS_DIR / "modele_dpe_v2.pkl"
    columns_path: Path = ARTIFACTS_DIR / "colonnes_modele_v2.pkl"
    zones_path: Path = ARTIFACTS_DIR / "zones_climatiques.pkl"
    embeddings_cache_path: Path = ARTIFACTS_DIR / "embeddings_documents.pkl"

    model_version: str = "v2-rf-2025"

    # Départements couverts par le simulateur (région PACA)
    departements_autorises: list[str] = ["04", "05", "06", "13", "83", "84"]


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance unique des réglages."""
    return Settings()


settings = get_settings()
