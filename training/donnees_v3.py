"""Données du modèle v3 : contrôle du coefficient, cible, découpage temporel, entrées.

- Test : exactement celui de reports/reference_v1.md (DPE établis après le 2026-08-30,
  mêmes exclusions via `evaluer.preparer_entrees`), avec l'étiquette réelle `etiquette_dpe`.
  Vérifié : effectif et répartition identiques à reference_v1.json, sinon arrêt.
- Validation : DPE établis du 2026-05-01 au 2026-08-30 (choix des modèles, calibration).
- Entraînement : DPE établis avant le 2026-05-01.
- Cible : étiquette au coefficient COEFFICIENT_CIBLE, depuis le coefficient des données
  publiées (contrôlé automatiquement : arrêt si la base a été republiée à un autre coefficient).

Usage : .venv/Scripts/python.exe -m training.donnees_v3   (écrit reports/donnees_v3.json)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.features_v3 import REGROUPEMENTS_CHAUFFAGE_ADEME, encoder
from app.ml.model import CLASSES_DPE, get_zones
from training.etiquettes import COEFFICIENT_PUBLIE, controler_coefficient_publie, etiquette_cible
from training.evaluer import CHAUFFAGE_ADEME, PERIODE_ADEME, TYPE_ADEME, preparer_entrees, repartition

RACINE = Path(__file__).resolve().parent.parent
ENTREE = RACINE / "data" / "dpe_paca.parquet"
REFERENCE = RACINE / "reports" / "reference_v1.json"
SORTIE = RACINE / "reports" / "donnees_v3.json"

COEFFICIENT_CIBLE = 1.9
DEBUT_VALIDATION = "2026-05-01"


@dataclass
class Jeux:
    entrees: dict[str, pd.DataFrame]  # entrées lisibles (surface, periode, …) par jeu
    y: dict[str, np.ndarray]
    brut: dict[str, pd.DataFrame]     # lignes ADEME correspondantes
    bilan: dict = field(default_factory=dict)

    def X(self, jeu: str, localisation: str) -> pd.DataFrame:
        return encoder(self.entrees[jeu], localisation)


def entrees_lisibles(df: pd.DataFrame) -> pd.DataFrame:
    """Libellés ADEME → entrées de l'API (avec les regroupements de chauffage du v3)."""
    chauffage = df["type_energie_principale_chauffage"].map(
        lambda l: CHAUFFAGE_ADEME[l].value if l in CHAUFFAGE_ADEME else REGROUPEMENTS_CHAUFFAGE_ADEME.get(l))
    zones = get_zones()
    e = pd.DataFrame({
        "surface": df["surface_habitable_logement"].astype(float),
        "periode": df["periode_construction"].map(lambda l: PERIODE_ADEME[l].value if l in PERIODE_ADEME else None),
        "type_batiment": df["type_batiment"].map(lambda l: TYPE_ADEME[l].value if l in TYPE_ADEME else None),
        "chauffage": chauffage,
        "departement": df["code_departement_ban"].astype(str),
    }, index=df.index)
    e["zone_climatique"] = e["departement"].map(zones)
    manquants = e.isna().any(axis=1)
    if manquants.any():
        raise ValueError(f"{int(manquants.sum())} lignes sans entrée valide : {e[manquants].head()}")
    return e


def empreinte(entrees: pd.DataFrame, y: np.ndarray) -> str:
    """SHA-256 des entrées et de la cible d'entraînement (indépendant de l'ordre des colonnes du parquet)."""
    h = hashlib.sha256()
    h.update(pd.util.hash_pandas_object(entrees.reset_index(drop=True), index=False).to_numpy().tobytes())
    h.update("".join(y).encode("utf-8"))
    return h.hexdigest()


def charger(chemin: Path = ENTREE) -> Jeux:
    df = pd.read_parquet(chemin).reset_index(drop=True)
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    coupure = reference["date_coupure"]

    controle = controler_coefficient_publie(df, attendu=COEFFICIENT_PUBLIE)
    df["cible"] = etiquette_cible(df, COEFFICIENT_CIBLE, coefficient_source=COEFFICIENT_PUBLIE)

    date = df["date_etablissement_dpe"].astype(str)
    masques = {
        "entrainement": date < DEBUT_VALIDATION,
        "validation": (date >= DEBUT_VALIDATION) & (date <= coupure),
    }
    # Test : mêmes lignes que reference_v1 (même sélection et mêmes exclusions)
    test_brut = df[date > coupure]
    entrees_api, exclusions = preparer_entrees(test_brut)
    test = test_brut.loc[entrees_api.index]
    if len(test) != reference["test_evalue"] or exclusions != reference["exclusions_test"]:
        raise AssertionError(f"Test différent de reference_v1 : {len(test)} lignes, exclusions {exclusions}")
    rep = repartition(test["etiquette_dpe"])
    if rep != reference["resultats"]["tous"]["repartition_reelle"]:
        raise AssertionError("Répartition des classes du test différente de reference_v1")

    brut = {nom: df[m] for nom, m in masques.items()}
    brut["test"] = test
    entrees = {nom: entrees_lisibles(b) for nom, b in brut.items()}
    y = {nom: b["cible"].to_numpy().astype(str) for nom, b in brut.items()}
    y["test"] = test["etiquette_dpe"].to_numpy().astype(str)  # étiquette réelle

    bilan = {
        "coefficient_cible": COEFFICIENT_CIBLE,
        "coefficient_publie_attendu": COEFFICIENT_PUBLIE,
        "controle_coefficient_publie": controle,
        "cible_differente_de_etiquette_dpe": int((df["cible"] != df["etiquette_dpe"].astype(str)).sum()),
        "date_coupure_test": coupure,
        "debut_validation": DEBUT_VALIDATION,
        "jeux": {nom: {"lignes": int(len(brut[nom])),
                       "du": str(brut[nom]["date_etablissement_dpe"].min()),
                       "au": str(brut[nom]["date_etablissement_dpe"].max()),
                       "repartition": repartition(pd.Series(y[nom]))}
                 for nom in ("entrainement", "validation", "test")},
        "chauffages_regroupes": {k: int((df["type_energie_principale_chauffage"] == k).sum())
                                 for k in REGROUPEMENTS_CHAUFFAGE_ADEME},
        "sha256_entrainement": empreinte(entrees["entrainement"], y["entrainement"]),
        "test_identique_a_reference_v1": True,
    }
    return Jeux(entrees=entrees, y=y, brut=brut, bilan=bilan)


def main() -> None:
    jeux = charger()
    SORTIE.write_bytes(json.dumps(jeux.bilan, ensure_ascii=False, indent=2).encode("utf-8"))
    for nom, j in jeux.bilan["jeux"].items():
        print(nom, j["lignes"], j["du"], j["au"])
    print("classes", CLASSES_DPE, "cible ≠ étiquette :", jeux.bilan["cible_differente_de_etiquette_dpe"])


if __name__ == "__main__":
    main()
