from functools import lru_cache

import joblib
import pandas as pd

from app.core.config import settings

# Les 7 classes DPE, toujours présentes dans la sortie
CLASSES_DPE = ["A", "B", "C", "D", "E", "F", "G"]


# Les .pkl sont produits par nos propres scripts de training/ et versionnés
# dans le dépôt : on les charge avec joblib en toute confiance.

@lru_cache
def get_model():
    """Charge le modèle Random Forest une seule fois."""
    return joblib.load(settings.model_path)


@lru_cache
def get_columns() -> list[str]:
    """Charge la liste ordonnée des colonnes du modèle une seule fois."""
    return list(joblib.load(settings.columns_path))


@lru_cache
def get_zones() -> dict[str, str]:
    """Charge la table département → zone climatique une seule fois."""
    return dict(joblib.load(settings.zones_path))


def zone_climatique(departement: str) -> str:
    """Zone climatique d'un département ; erreur si le département est inconnu."""
    zones = get_zones()
    if departement not in zones:
        raise ValueError(f"Aucune zone climatique connue pour le département {departement!r}")
    return zones[departement]


def predict(features: pd.DataFrame) -> tuple[str, dict[str, float]]:
    """Retourne la classe prédite et les probabilités des 7 classes (en nombres)."""
    modele = get_model()
    probas = modele.predict_proba(features)[0]
    par_classe = {str(classe): float(p) for classe, p in zip(modele.classes_, probas)}
    probabilites = {classe: par_classe.get(classe, 0.0) for classe in CLASSES_DPE}
    classe = max(probabilites, key=probabilites.get)
    return classe, probabilites
