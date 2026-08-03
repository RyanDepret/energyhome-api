from pydantic import BaseModel
from datetime import date
from typing import Optional

class LogementBase(BaseModel):
    surface: float
    annee_construction: int
    classe_dpe: str
    consommation_kwh: float
    type_chauffage: str
    ville: str
    code_postal: str
    date_diagnostic: date

class LogementCreate(LogementBase):
    pass

class LogementResponse(LogementBase):
    id: int

    class Config:
        from_attributes = True

class SimulateurInput(BaseModel):
    surface: float
    annee_construction: int

class PredictionInput(BaseModel):
    surface: float
    annee_construction: int
    consommation_kwh: float
    nb_pieces: int

class ChatInput(BaseModel):
    question: str
    locale: str = "fr"

class AgentInput(BaseModel):
    classe_dpe: str
    surface: float
    annee_construction: int
    consommation_kwh: float
    nb_pieces: int
    locale: str = "fr"

class ContactInput(BaseModel):
    nom: str
    email: str
    message: str