"""Calibration des probabilités multiclasses (une courbe par classe, puis renormalisation).

Utilisé à l'entraînement (training/calibrer_v3.py) et chargé par l'API avec le modèle v3.
"""

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

EPS = 1e-6


class Calibrateur:
    """Calibration « une classe contre les autres » : isotonique ou sigmoïde (Platt), puis
    renormalisation pour que les 7 probabilités somment à 1."""

    def __init__(self, methode: str):
        if methode not in ("isotonique", "sigmoide"):
            raise ValueError(f"Méthode inconnue : {methode}")
        self.methode = methode

    def fit(self, probas: np.ndarray, y_indices: np.ndarray) -> "Calibrateur":
        self.courbes_ = []
        for k in range(probas.shape[1]):
            cible = (y_indices == k).astype(int)
            p = probas[:, k]
            if self.methode == "isotonique":
                c = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p, cible)
            else:
                c = LogisticRegression(C=1e6).fit(_logit(p)[:, None], cible)
            self.courbes_.append(c)
        return self

    def transform(self, probas: np.ndarray) -> np.ndarray:
        cols = []
        for k, c in enumerate(self.courbes_):
            p = probas[:, k]
            cols.append(c.predict(p) if self.methode == "isotonique" else c.predict_proba(_logit(p)[:, None])[:, 1])
        q = np.clip(np.column_stack(cols), 0.0, 1.0)
        somme = q.sum(axis=1, keepdims=True)
        # Ligne entièrement nulle (cas extrême) : on garde les probabilités d'origine
        return np.where(somme > EPS, q / np.where(somme > EPS, somme, 1.0), probas)


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))
