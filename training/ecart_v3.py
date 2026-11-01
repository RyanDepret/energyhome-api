"""Écart entraînement / validation / test du modèle v3 (contrôle du sur-apprentissage).

Entraînement : métriques calculées ici, avec le modèle servi par l'API (artifacts/v3/modele.joblib,
via `app.ml.modele_v3.predire_lot`), calibration comprise, et aussi sans calibration.
Validation : reprise de reports/calibration_v3.json (calibration isotonique mesurée hors pli,
5 plis ; « aucune » pour les probabilités brutes). Test : reprise de reports/modele_v3.json.
Le test n'est pas relu : ses chiffres viennent du rapport de l'évaluation finale.

Sorties : reports/ecart_v3.json (repris dans la fiche par training/fiche_v3.py)

Usage : .venv/Scripts/python.exe -m training.ecart_v3
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.ml.modele_v3 import charger as charger_modele
from app.ml.modele_v3 import predire_lot
from training.comparer_modeles import evaluer_probas
from training.donnees_v3 import charger

RACINE = Path(__file__).resolve().parent.parent
MODELE = RACINE / "artifacts" / "v3"
SORTIE = RACINE / "reports" / "ecart_v3.json"
CLES = ("accuracy", "accuracy_a_une_classe_pres", "brier_multiclasse")


def lire(nom: str) -> dict:
    return json.loads((RACINE / "reports" / nom).read_text(encoding="utf-8"))


def main() -> None:
    artefact = charger_modele(MODELE)
    calibration = lire("calibration_v3.json")
    test = lire("modele_v3.json")["resultats"]["tous"]["v3"]
    if calibration["methode_retenue"] != "isotonique" or artefact["calibrateur"] is None:
        raise AssertionError("Le script suppose la calibration isotonique du modèle exporté")

    jeux = charger()
    entrees, y = jeux.entrees["entrainement"], jeux.y["entrainement"]
    calibrees = predire_lot(artefact, entrees)
    brutes = artefact["classifieur"].predict_proba(jeux.X("entrainement", artefact["localisation"]))

    garder = lambda m: {k: float(m[k]) for k in CLES}  # noqa: E731
    sortie = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lignes": {"entrainement": int(len(y)), "validation": int(jeux.bilan["jeux"]["validation"]["lignes"]),
                   "test": int(test["effectif"])},
        "calibre": {"entrainement": garder(evaluer_probas(y, calibrees)),
                    "validation": garder(calibration["calibration"]["isotonique"]),
                    "test": garder(test)},
        "brut": {"entrainement": garder(evaluer_probas(y, brutes)),
                 "validation": garder(calibration["calibration"]["aucune"])},
    }
    SORTIE.write_bytes(json.dumps(sortie, ensure_ascii=False, indent=2).encode("utf-8"))
    print(json.dumps(sortie, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
