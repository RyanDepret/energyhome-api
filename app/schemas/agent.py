from pydantic import BaseModel


class AgentInput(BaseModel):
    classe_dpe: str
    surface: float
    annee_construction: int
    type_batiment: str
    type_chauffage: str
    code_postal: str
    locale: str = "fr"
