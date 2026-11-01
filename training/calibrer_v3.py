"""Calibration du modèle retenu et courbe d'apprentissage (validation uniquement).

Calibration : isotonique et sigmoïde comparées par validation croisée en 5 plis SUR LA
VALIDATION (le calibrateur est appris sur 4 plis, mesuré sur le 5e) ; la méthode retenue
(ou aucune si aucune n'améliore le Brier) est ensuite apprise sur toute la validation.

Courbe d'apprentissage : même famille et mêmes réglages, entraînés sur 10 000, 50 000,
200 000 lignes puis tout l'entraînement, mesurés sur la validation.

Entrées : reports/comparaison_v3.json (modèle retenu, réentraîné à l'identique)
Sorties : reports/calibration_v3.json, reports/calibration_v3.md,
          data/modeles_v3/modele_calibre.joblib (non commité)

Usage : .venv/Scripts/python.exe -m training.calibrer_v3
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import StratifiedKFold

from app.ml.calibration import Calibrateur
from app.ml.model import CLASSES_DPE
from training.comparer_modeles import DOSSIER_MODELES, chrono, entrainer_lgbm, evaluer_probas, probas_7_classes
from training.donnees_v3 import charger
from training.evaluer import GRAINE, brier_multiclasse, fiabilite

RACINE = Path(__file__).resolve().parent.parent
COMPARAISON = RACINE / "reports" / "comparaison_v3.json"
SORTIE_JSON = RACINE / "reports" / "calibration_v3.json"
SORTIE_MD = RACINE / "reports" / "calibration_v3.md"
MODELE_CALIBRE = DOSSIER_MODELES / "modele_calibre.joblib"

TAILLES_COURBE = [10_000, 50_000, 200_000, None]  # None = tout l'entraînement
N_PLIS = 5


def calibration_croisee(probas: np.ndarray, y: np.ndarray, methode: str) -> np.ndarray:
    """Probabilités calibrées hors pli (chaque ligne calibrée par un calibrateur qui ne l'a pas vue)."""
    yi = np.array([CLASSES_DPE.index(c) for c in y])
    sortie = np.empty_like(probas)
    for app, val in StratifiedKFold(N_PLIS, shuffle=True, random_state=GRAINE).split(probas, yi):
        sortie[val] = Calibrateur(methode).fit(probas[app], yi[app]).transform(probas[val])
    return sortie


def main() -> None:
    comparaison = json.loads(COMPARAISON.read_text(encoding="utf-8"))
    choix = next(r for r in comparaison["resultats"] if r["nom"] == comparaison["choix"])
    if choix["famille"] not in ("lightgbm", "localisation"):
        raise NotImplementedError(f"Calibration prévue pour LightGBM ; modèle retenu : {choix['nom']}")
    loc = comparaison["localisation_retenue"]

    jeux = charger()
    X, y = jeux.X("entrainement", loc), jeux.y["entrainement"]
    Xv, yv = jeux.X("validation", loc), jeux.y["validation"]

    # Réentraînement du modèle retenu avec ses réglages (entraînement déterministe, graine fixe) ;
    # on vérifie qu'il reproduit exactement le score de la comparaison
    modele = entrainer_lgbm(X, y, Xv, yv, choix["params"])
    brutes = probas_7_classes(modele, Xv)
    if not np.isclose(brier_multiclasse(yv, brutes), choix["validation"]["brier_multiclasse"], rtol=0, atol=1e-9):
        raise AssertionError("Le modèle réentraîné ne reproduit pas le Brier de la comparaison")

    # ── Calibration ──
    methodes = {"aucune": brutes}
    for m in ("isotonique", "sigmoide"):
        methodes[m] = calibration_croisee(brutes, yv, m)
    calib = {nom: {**evaluer_probas(yv, p), "fiabilite": fiabilite(yv, p)} for nom, p in methodes.items()}
    retenue = min(calib, key=lambda k: calib[k]["brier_multiclasse"])
    calibrateur = None
    if retenue != "aucune":
        calibrateur = Calibrateur(retenue).fit(brutes, np.array([CLASSES_DPE.index(c) for c in yv]))
    joblib.dump({"classifieur": modele, "calibrateur": calibrateur, "localisation": loc,
                 "colonnes": list(Xv.columns), "params": choix["params"],
                 "meilleure_iteration": int(modele.best_iteration_)}, MODELE_CALIBRE, compress=3)

    # ── Courbe d'apprentissage ──
    courbe = []
    rng = np.random.default_rng(GRAINE)
    for taille in TAILLES_COURBE:
        if taille is None or taille >= len(X):
            idx, n = np.arange(len(X)), len(X)
        else:
            idx, n = rng.choice(len(X), size=taille, replace=False), taille
        m, s = chrono(lambda: entrainer_lgbm(X.iloc[idx], y[idx], Xv, yv, choix["params"]))
        r = evaluer_probas(yv, probas_7_classes(m, Xv))
        courbe.append({"lignes": int(n), "secondes": round(s, 1), "meilleure_iteration": int(m.best_iteration_),
                       **{k: r[k] for k in ("accuracy", "f1_macro", "accuracy_a_une_classe_pres", "brier_multiclasse")}})
        print(courbe[-1], flush=True)

    sortie = {"genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "modele": choix["nom"], "localisation": loc, "plis": N_PLIS,
              "calibration": calib, "methode_retenue": retenue, "courbe_apprentissage": courbe}
    SORTIE_JSON.write_bytes(json.dumps(sortie, ensure_ascii=False, indent=2).encode("utf-8"))
    SORTIE_MD.write_bytes(rapport(sortie).encode("utf-8"))
    print("Méthode retenue :", retenue)


def _p(x) -> str:
    return "—" if x is None else f"{100 * x:.1f} %"


def _n(x) -> str:
    return f"{x:,}".replace(",", " ")


def rapport(s: dict) -> str:
    c = s["calibration"]
    l = ["# Calibration et courbe d'apprentissage du modèle v3", "",
         f"Généré par `training/calibrer_v3.py` le {s['genere_le']}. Modèle : {s['modele']} "
         f"(localisation : {s['localisation']}).", "",
         "## Calibration (validation, 5 plis)", "",
         f"Chaque méthode est apprise sur 4 plis de la validation et mesurée sur le 5e. "
         f"Méthode retenue (plus petit Brier) : **{s['methode_retenue']}**.", "",
         "| | Sans calibration | Isotonique | Sigmoïde |", "|---|---:|---:|---:|"]
    for cle, lib in (("brier_multiclasse", "Brier multiclasse"), ("accuracy", "Accuracy"), ("f1_macro", "F1 macro"),
                     ("accuracy_a_une_classe_pres", "À une classe près")):
        f = (lambda v: f"{v:.4f}") if cle == "brier_multiclasse" else _p
        l.append(f"| {lib} | {f(c['aucune'][cle])} | {f(c['isotonique'][cle])} | {f(c['sigmoide'][cle])} |")
    for nom in ("aucune", "isotonique", "sigmoide"):
        l += ["", f"Fiabilité — {'sans calibration' if nom == 'aucune' else nom} :", "",
              "| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |", "|---|---:|---:|---:|"]
        for t in c[nom]["fiabilite"]:
            l.append(f"| {t['tranche']} | {_n(t['effectif'])} | {_p(t['probabilite_moyenne_annoncee'])} | "
                     f"{_p(t['taux_bonnes_reponses'])} |")
    l += ["", "## Courbe d'apprentissage (validation, sans calibration)", "",
          "| Lignes d'entraînement | Accuracy | F1 macro | À une classe près | Brier | Itérations | Temps |",
          "|---:|---:|---:|---:|---:|---:|---:|"]
    for r in s["courbe_apprentissage"]:
        l.append(f"| {_n(r['lignes'])} | {_p(r['accuracy'])} | {_p(r['f1_macro'])} | {_p(r['accuracy_a_une_classe_pres'])} | "
                 f"{r['brier_multiclasse']:.4f} | {r['meilleure_iteration']} | {r['secondes']:.0f} s |")
    return "\n".join(l) + "\n"


if __name__ == "__main__":
    main()
