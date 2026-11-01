import re
from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import settings


# ── ENUMS : codes simples exposés par l'API ↔ libellés ADEME exacts du modèle ─

class Periode(str, Enum):
    """Période de construction, une valeur par colonne `periode_construction_*` du modèle."""

    AVANT_1948 = "avant_1948"
    P_1948_1974 = "1948_1974"
    P_1975_1977 = "1975_1977"
    P_1978_1982 = "1978_1982"
    P_1983_1988 = "1983_1988"
    P_1989_2000 = "1989_2000"
    P_2001_2005 = "2001_2005"
    P_2006_2012 = "2006_2012"
    P_2013_2021 = "2013_2021"
    APRES_2021 = "apres_2021"


PERIODE_LABELS: dict[Periode, str] = {
    Periode.AVANT_1948: "avant 1948",
    Periode.P_1948_1974: "1948-1974",
    Periode.P_1975_1977: "1975-1977",
    Periode.P_1978_1982: "1978-1982",
    Periode.P_1983_1988: "1983-1988",
    Periode.P_1989_2000: "1989-2000",
    Periode.P_2001_2005: "2001-2005",
    Periode.P_2006_2012: "2006-2012",
    Periode.P_2013_2021: "2013-2021",
    Periode.APRES_2021: "après 2021",
}


class TypeBatiment(str, Enum):
    """Type de bâtiment, identique au libellé ADEME."""

    MAISON = "maison"
    APPARTEMENT = "appartement"


TYPE_BATIMENT_LABELS: dict[TypeBatiment, str] = {
    TypeBatiment.MAISON: "maison",
    TypeBatiment.APPARTEMENT: "appartement",
}


class Chauffage(str, Enum):
    """Énergie principale de chauffage."""

    ELECTRICITE = "electricite"
    ELECTRICITE_RENOUVELABLE = "electricite_renouvelable"
    GAZ_NATUREL = "gaz_naturel"
    FIOUL = "fioul"
    GPL = "gpl"
    PROPANE = "propane"
    BOIS_BUCHES = "bois_buches"
    BOIS_GRANULES = "bois_granules"
    BOIS_PLAQUETTES = "bois_plaquettes"
    RESEAU_CHALEUR = "reseau_chaleur"


# Libellés recopiés depuis colonnes_modele_v2.pkl : tirets longs « – »,
# apostrophe typographique pour « Plaquettes d’industrie », droite pour « d'origine »
CHAUFFAGE_LABELS: dict[Chauffage, str] = {
    Chauffage.ELECTRICITE: "Électricité",
    Chauffage.ELECTRICITE_RENOUVELABLE: "Électricité d'origine renouvelable utilisée dans le bâtiment",
    Chauffage.GAZ_NATUREL: "Gaz naturel",
    Chauffage.FIOUL: "Fioul domestique",
    Chauffage.GPL: "GPL",
    Chauffage.PROPANE: "Propane",
    Chauffage.BOIS_BUCHES: "Bois – Bûches",
    Chauffage.BOIS_GRANULES: "Bois – Granulés (pellets) ou briquettes",
    Chauffage.BOIS_PLAQUETTES: "Bois – Plaquettes d’industrie",
    Chauffage.RESEAU_CHALEUR: "Réseau de Chauffage urbain",
}


# ── ENTRÉE / SORTIE DE /predict ───────────────────────────────────────────────

class PredictionInput(BaseModel):
    """Description du logement à évaluer. Fournir `periode` OU `annee_construction`."""

    surface: float = Field(ge=9, le=1000, description="Surface habitable en m²")
    periode: Periode | None = None
    annee_construction: int | None = Field(default=None, ge=1800)
    type_batiment: TypeBatiment
    chauffage: Chauffage
    code_postal: str

    @field_validator("annee_construction")
    @classmethod
    def annee_pas_dans_le_futur(cls, annee: int | None) -> int | None:
        annee_courante = date.today().year
        if annee is not None and annee > annee_courante:
            raise ValueError(f"annee_construction doit être comprise entre 1800 et {annee_courante}")
        return annee

    @field_validator("code_postal")
    @classmethod
    def code_postal_paca(cls, code_postal: str) -> str:
        if not re.fullmatch(r"\d{5}", code_postal):
            raise ValueError("Le code postal doit contenir exactement 5 chiffres.")
        departements = settings.departements_autorises
        if code_postal[:2] not in departements:
            raise ValueError(
                "Ce simulateur est actuellement disponible uniquement pour la région PACA "
                f"({', '.join(departements)})."
            )
        return code_postal

    @model_validator(mode="after")
    def periode_ou_annee(self) -> "PredictionInput":
        if (self.periode is None) == (self.annee_construction is None):
            raise ValueError("Fournir exactement un des deux champs : periode ou annee_construction.")
        return self


class Importance(BaseModel):
    """Poids d'un critère dans la prédiction (contributions SHAP, somme des poids = 1)."""

    critere: str
    valeur: Any
    poids: float = Field(ge=0, le=1)


class PredictionOutput(BaseModel):
    """Classe DPE prédite, probabilités des 7 classes et facteurs explicatifs."""

    classe: str
    probabilites: dict[str, float]
    importances: list[Importance] = []
    model_version: str
    entree: dict[str, Any]
