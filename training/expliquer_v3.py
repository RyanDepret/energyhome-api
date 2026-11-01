"""Explications du modèle v3 : importance globale, contrôle SHAP, temps de réponse.

- Importance globale : moyenne de |contribution SHAP| par variable sur la validation,
  pour la classe prédite (ce que voit l'utilisateur) et toutes classes confondues.
- Contrôles : (1) additivité — contributions + terme constant = sortie brute du modèle
  (log-odds de chaque classe), contrôle indépendant du calcul ; (2) concordance avec la
  bibliothèque shap (TreeExplainer), qui pour LightGBM délègue au même calcul natif.
- Temps : `expliquer` et `predire` complets, mesurés sur 300 logements de la validation.

Sorties : reports/explications_v3.json, reports/explications_v3.md

Usage : .venv/Scripts/python.exe -m training.expliquer_v3
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from app.ml.features_v3 import LIBELLES_CRITERES, encoder
from app.ml.modele_v3 import CLASSES_DPE, contributions, expliquer, predire, predire_lot
from training.calibrer_v3 import MODELE_CALIBRE
from training.donnees_v3 import charger
from training.evaluer import GRAINE

RACINE = Path(__file__).resolve().parent.parent
SORTIE_JSON = RACINE / "reports" / "explications_v3.json"
SORTIE_MD = RACINE / "reports" / "explications_v3.md"
N_CONTROLE_SHAP = 1000
N_CHRONO = 300
LIMITE_MS = 200


def main() -> None:
    # Fichier produit localement par training/calibrer_v3.py : chargement joblib sûr
    artefact = joblib.load(MODELE_CALIBRE)
    jeux = charger()
    entrees = jeux.entrees["validation"].reset_index(drop=True)
    colonnes = artefact["colonnes"]

    # Importance globale
    contrib = contributions(artefact, entrees)                         # n × 7 × variables
    pred = predire_lot(artefact, entrees).argmax(axis=1)
    classe_predite = np.abs(contrib[np.arange(len(entrees)), pred])     # n × variables
    globale_predite = classe_predite.mean(axis=0)
    globale_toutes = np.abs(contrib).sum(axis=1).mean(axis=0)
    importance = {
        col: {"critere": LIBELLES_CRITERES[col],
              "classe_predite": float(globale_predite[i]), "part_classe_predite": float(globale_predite[i] / globale_predite.sum()),
              "toutes_classes": float(globale_toutes[i]), "part_toutes_classes": float(globale_toutes[i] / globale_toutes.sum())}
        for i, col in enumerate(colonnes)}

    # Contrôle avec la bibliothèque shap
    rng = np.random.default_rng(GRAINE)
    idx = rng.choice(len(entrees), size=N_CONTROLE_SHAP, replace=False)
    Xs = encoder(entrees.iloc[idx], artefact["localisation"])
    booster = artefact["classifieur"].booster_
    valeurs = shap.TreeExplainer(booster).shap_values(Xs)
    valeurs = np.stack(valeurs, axis=1) if isinstance(valeurs, list) else np.transpose(valeurs, (0, 2, 1))
    ecart_max = float(np.abs(valeurs - contrib[idx]).max())
    complet = np.asarray(booster.predict(Xs, pred_contrib=True)).reshape(len(Xs), len(CLASSES_DPE), -1)
    brut = np.asarray(booster.predict(Xs, raw_score=True))
    ecart_additivite = float(np.abs(complet.sum(axis=2) - brut).max())

    # Temps de réponse
    lignes = entrees.iloc[rng.choice(len(entrees), size=N_CHRONO, replace=False)].to_dict(orient="records")
    expliquer(artefact, lignes[0])  # premier appel hors mesure
    temps_expl, temps_pred = [], []
    for e in lignes:
        t0 = time.perf_counter(); expliquer(artefact, e); temps_expl.append(1000 * (time.perf_counter() - t0))
        t0 = time.perf_counter(); predire(artefact, e); temps_pred.append(1000 * (time.perf_counter() - t0))
    temps = {nom: {"mediane_ms": float(np.median(t)), "p95_ms": float(np.percentile(t, 95)), "max_ms": float(np.max(t))}
             for nom, t in (("expliquer", temps_expl), ("predire_complet", temps_pred))}

    exemple = lignes[0]
    sortie = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lignes_validation": len(entrees),
        "importance_globale": importance,
        "controle_shap": {"lignes": N_CONTROLE_SHAP, "version_shap": shap.__version__, "ecart_absolu_max": ecart_max,
                          "ecart_additivite_max": ecart_additivite},
        "temps": temps, "limite_ms": LIMITE_MS,
        "exemple": {"entree": exemple, "facteurs": expliquer(artefact, exemple),
                    "classe": CLASSES_DPE[int(predire_lot(artefact, pd.DataFrame([exemple]))[0].argmax())]},
    }
    SORTIE_JSON.write_bytes(json.dumps(sortie, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    SORTIE_MD.write_bytes(rapport(sortie).encode("utf-8"))
    print(json.dumps({"ecart_shap": ecart_max, "ecart_additivite": ecart_additivite, "temps": temps}, indent=1))


def rapport(s: dict) -> str:
    l = ["# Explications du modèle v3", "",
         f"Généré par `training/expliquer_v3.py` le {s['genere_le']}, sur les "
         f"{s['lignes_validation']:,} DPE de la validation.".replace(f"{s['lignes_validation']:,}",
                                                                   f"{s['lignes_validation']:,}".replace(",", " ")), "",
         "## Importance globale des variables", "",
         "Moyenne de |contribution SHAP| (en log-odds), calculée par LightGBM (`pred_contrib`).", "",
         "| Variable | Classe prédite | Part | Toutes classes | Part |", "|---|---:|---:|---:|---:|"]
    for v in sorted(s["importance_globale"].values(), key=lambda v: -v["classe_predite"]):
        l.append(f"| {v['critere']} | {v['classe_predite']:.3f} | {100 * v['part_classe_predite']:.1f} % | "
                 f"{v['toutes_classes']:.3f} | {100 * v['part_toutes_classes']:.1f} % |")
    c = s["controle_shap"]
    l += ["", "## Contrôles des contributions", "",
          f"Sur {c['lignes']} lignes tirées au hasard :", "",
          f"- **Additivité** (contrôle indépendant) : contributions + terme constant = sortie brute du modèle pour "
          f"chaque classe, à {c['ecart_additivite_max']:.2e} près au maximum.",
          f"- **Bibliothèque shap** ({c['version_shap']}) : écart maximal {c['ecart_absolu_max']:.2e} avec les "
          "contributions de l'API. Ce n'est pas une vérification indépendante : pour un modèle LightGBM, "
          "`shap.TreeExplainer` délègue au même calcul natif (`pred_contrib`). Elle confirme seulement que l'API "
          "fournit les mêmes valeurs que shap, qui n'est donc pas nécessaire en production.",
          "", "## Temps de réponse", "", f"Limite visée : {s['limite_ms']} ms par prédiction.", "",
          "| Fonction | Médiane | 95e centile | Maximum |", "|---|---:|---:|---:|"]
    for nom, t in s["temps"].items():
        l.append(f"| `{nom}` | {t['mediane_ms']:.1f} ms | {t['p95_ms']:.1f} ms | {t['max_ms']:.1f} ms |")
    e = s["exemple"]
    l += ["", "## Exemple de sortie `importances`", "", f"Entrée : `{json.dumps(e['entree'], ensure_ascii=False)}`, "
          f"classe prédite **{e['classe']}**.", "", "| critere | valeur | poids |", "|---|---|---:|"]
    l += [f"| {f['critere']} | {f['valeur']} | {f['poids']:.3f} |" for f in e["facteurs"]]
    return "\n".join(l) + "\n"


if __name__ == "__main__":
    main()
