"""Export des artefacts du modèle v3 dans artifacts/v3/ (après l'évaluation finale).

  modele.joblib     classifieur + calibrateur + localisation + colonnes
  colonnes.json     colonnes d'entrée, dans l'ordre du modèle
  metadonnees.json  version, date, coefficient cible, empreinte SHA-256 des données
                    d'entraînement, métriques de test, versions des bibliothèques

Usage : .venv/Scripts/python.exe -m training.exporter_v3
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib

from app.core.config import Settings
from training.calibrer_v3 import MODELE_CALIBRE

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "artifacts" / "v3"
VERSION = "v3-lightgbm-2026-11"
BIBLIOTHEQUES = ["lightgbm", "scikit-learn", "numpy", "pandas", "joblib", "scipy"]


def sha256(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def lire(nom: str) -> dict:
    return json.loads((RACINE / "reports" / nom).read_text(encoding="utf-8"))


def main() -> None:
    if Settings.model_fields["model_version"].default != VERSION:
        raise AssertionError("La version par défaut de app/core/config.py doit être celle exportée")
    donnees, comparaison, calibration, test = (lire(n) for n in (
        "donnees_v3.json", "comparaison_v3.json", "calibration_v3.json", "modele_v3.json"))
    # Fichier produit localement par training/calibrer_v3.py : chargement joblib sûr
    artefact = joblib.load(MODELE_CALIBRE)

    DOSSIER.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefact, DOSSIER / "modele.joblib", compress=3)
    (DOSSIER / "colonnes.json").write_bytes(json.dumps(artefact["colonnes"], ensure_ascii=False, indent=2).encode("utf-8"))

    cles = ("accuracy", "f1_macro", "accuracy_a_une_classe_pres", "brier_multiclasse")
    meta = {
        "version": VERSION,
        "date_export": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modele": comparaison["choix"],
        "hyperparametres": artefact["params"],
        "meilleure_iteration": artefact["meilleure_iteration"],
        "localisation": artefact["localisation"],
        "colonnes": artefact["colonnes"],
        "calibration": calibration["methode_retenue"],
        "coefficient_electricite_cible": donnees["coefficient_cible"],
        "coefficient_electricite_donnees_publiees": donnees["controle_coefficient_publie"],
        "donnees": {
            "source": "ADEME, DPE logements existants (dpe03existant), région PACA",
            "entrainement": donnees["jeux"]["entrainement"],
            "validation": donnees["jeux"]["validation"],
            "test": {k: donnees["jeux"]["test"][k] for k in ("lignes", "du", "au")},
            "sha256_entrainement": donnees["sha256_entrainement"],
        },
        "metriques_test": {g: {k: r["v3"][k] for k in cles} for g, r in test["resultats"].items()},
        "references_test": {
            "classe_majoritaire": {k: test["resultats"]["tous"]["classe_majoritaire"][k]
                                   for k in ("accuracy", "accuracy_a_une_classe_pres")},
            "brier_repartition_constante": test["resultats"]["tous"]["brier_reference_repartition_constante"],
        },
        "python": platform.python_version(),
        "bibliotheques": {b: version(b) for b in BIBLIOTHEQUES},
        "sha256_modele_joblib": sha256(DOSSIER / "modele.joblib"),
    }
    (DOSSIER / "metadonnees.json").write_bytes(json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
    print(f"Artefacts écrits dans {DOSSIER} ({(DOSSIER / 'modele.joblib').stat().st_size / 1e6:.2f} Mo)")


if __name__ == "__main__":
    main()
