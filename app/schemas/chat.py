from typing import Literal

from pydantic import BaseModel


class ChatInput(BaseModel):
    question: str
    locale: str = "fr"
    # Modèle de génération ; la recherche documentaire (et donc les sources) est la même pour les deux
    modele: Literal["claude", "mistral"] = "claude"


class Source(BaseModel):
    extrait: str
    score: float


class Tokens(BaseModel):
    entree: int
    sortie: int


class ChatOutput(BaseModel):
    question: str
    reponse: str
    sources: list[Source]
    modele: Literal["claude", "mistral"]
    # Temps de génération seul (hors recherche documentaire), nouvelles tentatives comprises
    duree_ms: int
    # Absent si le fournisseur ne renvoie pas l'usage
    tokens: Tokens | None = None
