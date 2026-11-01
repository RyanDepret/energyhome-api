"""Modèle v3 : chargement, prédiction calibrée et explication d'une prédiction.

Artefacts (artifacts/v3/, produits par training/exporter_v3.py) :
  modele.joblib      classifieur LightGBM + calibrateur + localisation + colonnes
  colonnes.json      colonnes d'entrée dans l'ordre du modèle
  metadonnees.json   version, date, coefficient cible, empreinte des données, métriques, bibliothèques

Explications : contributions SHAP exactes calculées par LightGBM (`pred_contrib=True`),
pour la classe prédite, en valeur absolue et ramenées à une somme de 1.
"""

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.ml.features_v3 import LIBELLES_CRITERES, encoder

CLASSES_DPE = ["A", "B", "C", "D", "E", "F", "G"]


@lru_cache
def charger(dossier: Path) -> dict:
    """Charge les artefacts v3 une seule fois.

    Les .joblib sont produits par nos scripts de training/ et versionnés dans le dépôt :
    on les charge avec joblib en toute confiance.
    """
    artefact = joblib.load(dossier / "modele.joblib")
    meta = json.loads((dossier / "metadonnees.json").read_text(encoding="utf-8"))
    colonnes = json.loads((dossier / "colonnes.json").read_text(encoding="utf-8"))
    if colonnes != artefact["colonnes"]:
        raise ValueError("colonnes.json ne correspond pas au modèle enregistré")
    classes = [str(c) for c in artefact["classifieur"].classes_]
    if classes != CLASSES_DPE:
        raise ValueError(f"Classes du modèle inattendues : {classes}")
    return {**artefact, "metadonnees": meta}


def _matrice(artefact: dict, entrees: pd.DataFrame) -> pd.DataFrame:
    return encoder(entrees, artefact["localisation"])


def predire_lot(artefact: dict, entrees: pd.DataFrame) -> np.ndarray:
    """Probabilités calibrées (n × 7, ordre A…G)."""
    brutes = artefact["classifieur"].predict_proba(_matrice(artefact, entrees))
    calibrateur = artefact["calibrateur"]
    return brutes if calibrateur is None else calibrateur.transform(brutes)


def contributions(artefact: dict, entrees: pd.DataFrame) -> np.ndarray:
    """Contributions SHAP (n × 7 classes × variables), sans le terme constant."""
    X = _matrice(artefact, entrees)
    brut = artefact["classifieur"].booster_.predict(X, pred_contrib=True)
    return np.asarray(brut).reshape(len(X), len(CLASSES_DPE), X.shape[1] + 1)[:, :, :-1]


def expliquer(artefact: dict, entree: dict, classe: str | None = None) -> list[dict]:
    """Facteurs de la prédiction : `critere`, `valeur`, `poids` (entre 0 et 1, somme 1), par poids décroissant."""
    entrees = pd.DataFrame([entree])
    if classe is None:
        classe = CLASSES_DPE[int(predire_lot(artefact, entrees)[0].argmax())]
    c = np.abs(contributions(artefact, entrees)[0, CLASSES_DPE.index(classe)])
    total = c.sum()
    poids = c / total if total > 0 else np.full(len(c), 1 / len(c))
    facteurs = [{"critere": LIBELLES_CRITERES[col], "valeur": entree[col], "poids": float(p)}
                for col, p in zip(artefact["colonnes"], poids)]
    return sorted(facteurs, key=lambda f: -f["poids"])


def predire(artefact: dict, entree: dict) -> tuple[str, dict[str, float], list[dict]]:
    """Classe, probabilités calibrées des 7 classes et facteurs explicatifs d'un logement."""
    probas = predire_lot(artefact, pd.DataFrame([entree]))[0]
    probabilites = {c: float(p) for c, p in zip(CLASSES_DPE, probas)}
    classe = max(probabilites, key=probabilites.get)
    return classe, probabilites, expliquer(artefact, entree, classe)
