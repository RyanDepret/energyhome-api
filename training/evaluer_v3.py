"""Évaluation finale du modèle v3 sur le test temporel — une seule fois.

Même test, mêmes références et même présentation que reports/reference_v1.md, plus la
comparaison directe v1 / v3 / références. Les probabilités sont calculées avec le code
de l'API (`app.ml.modele_v3.predire_lot`), calibration comprise.

Le script refuse de tourner si reports/modele_v3.json existe déjà (le test ne sert qu'une
fois) ; `--refaire` force une nouvelle exécution, qui serait alors signalée dans le rapport.

Entrées : data/modeles_v3/modele_calibre.joblib, reports/reference_v1.json, comparaison/calibration v3
Sorties : reports/modele_v3.json, reports/modele_v3.md

Usage : .venv/Scripts/python.exe -m training.evaluer_v3
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from app.ml.model import CLASSES_DPE
from app.ml.modele_v3 import predire_lot
from training.calibrer_v3 import MODELE_CALIBRE
from training.donnees_v3 import charger
from training.evaluer import GRAINE, _fiabilite, _matrice, _n, _p, est_electrique, evaluer_groupe

RACINE = Path(__file__).resolve().parent.parent
REFERENCE = RACINE / "reports" / "reference_v1.json"
COMPARAISON = RACINE / "reports" / "comparaison_v3.json"
CALIBRATION = RACINE / "reports" / "calibration_v3.json"
SORTIE_JSON = RACINE / "reports" / "modele_v3.json"
SORTIE_MD = RACINE / "reports" / "modele_v3.md"

GROUPES = {"tous": "Tous les logements", "chauffage_electrique": "Chauffage principal électrique",
           "autres_chauffages": "Autres chauffages"}


def verdicts(r: dict) -> dict:
    v3, maj, alea = r["v3"], r["classe_majoritaire"], r["aleatoire_selon_repartition"]
    return {
        "accuracy_vs_classe_majoritaire": v3["accuracy"] > maj["accuracy"],
        "a_une_classe_pres_vs_classe_majoritaire": v3["accuracy_a_une_classe_pres"] > maj["accuracy_a_une_classe_pres"],
        "accuracy_vs_aleatoire": v3["accuracy"] > alea["accuracy"],
        "brier_vs_repartition_constante": v3["brier_multiclasse"] < r["brier_reference_repartition_constante"],
        "accuracy_vs_v1": v3["accuracy"] > r["v1"]["accuracy"],
        "brier_vs_v1": v3["brier_multiclasse"] < r["v1"]["brier_multiclasse"],
    }


def phrase(r: dict) -> str:
    v3, maj, alea = r["v3"], r["classe_majoritaire"], r["aleatoire_selon_repartition"]
    v = r["verdicts"]
    b = lambda ok: "bat" if ok else "ne bat pas"  # noqa: E731
    return (f"Le modèle v3 **{b(v['accuracy_vs_classe_majoritaire'])}** « toujours {r['classe_majoritaire_nom']} » en accuracy "
            f"({_p(v3['accuracy'])} contre {_p(maj['accuracy'])}), **{b(v['a_une_classe_pres_vs_classe_majoritaire'])}** "
            f"cette référence à une classe près ({_p(v3['accuracy_a_une_classe_pres'])} contre "
            f"{_p(maj['accuracy_a_une_classe_pres'])}), **{b(v['accuracy_vs_aleatoire'])}** le tirage aléatoire "
            f"({_p(v3['accuracy'])} contre {_p(alea['accuracy'])}) et **{b(v['brier_vs_repartition_constante'])}** la "
            f"répartition constante en score de Brier ({v3['brier_multiclasse']:.4f} contre "
            f"{r['brier_reference_repartition_constante']:.4f}).")


def tableau(r: dict) -> str:
    cols = [("v3", "Modèle v3"), ("v1", "Modèle v1 (actuel)"), ("classe_majoritaire", "Classe majoritaire"),
            ("aleatoire_selon_repartition", "Aléatoire selon la répartition")]
    l = ["| | " + " | ".join(c[1] for c in cols) + " |", "|---|" + "---:|" * len(cols)]
    for cle, lib in (("accuracy", "Accuracy"), ("f1_macro", "F1 macro"),
                     ("accuracy_a_une_classe_pres", "Accuracy à une classe près")):
        l.append(f"| {lib} | " + " | ".join(_p(r[c][cle]) for c, _ in cols) + " |")
    l.append(f"| Brier multiclasse | {r['v3']['brier_multiclasse']:.4f} | {r['v1']['brier_multiclasse']:.4f} | — | "
             f"{r['brier_reference_repartition_constante']:.4f} (répartition constante) |")
    for c in CLASSES_DPE:
        l.append(f"| F1 classe {c} | " + " | ".join(f"{r[k]['f1_par_classe'][c]:.3f}" for k, _ in cols) + " |")
    return "\n".join(l)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refaire", action="store_true", help="réévaluer malgré un rapport existant")
    args = parser.parse_args()
    if SORTIE_JSON.exists() and not args.refaire:
        raise SystemExit(f"{SORTIE_JSON.name} existe déjà : le test a déjà servi. Utilisez --refaire en connaissance de cause.")

    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    comparaison = json.loads(COMPARAISON.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    # Fichier produit localement par training/calibrer_v3.py : chargement joblib sûr
    artefact = joblib.load(MODELE_CALIBRE)

    jeux = charger()
    test, entrees, y = jeux.brut["test"], jeux.entrees["test"], jeux.y["test"]
    probas = predire_lot(artefact, entrees)

    rep = reference["references"]["repartition_avant_coupure"]
    prior = np.array([rep["effectifs"][c] for c in CLASSES_DPE], dtype=float)
    prior /= prior.sum()
    majoritaire = reference["references"]["classe_majoritaire"]

    elec = est_electrique(test).to_numpy()
    masques = {"tous": np.ones(len(test), dtype=bool), "chauffage_electrique": elec, "autres_chauffages": ~elec}
    resultats = {}
    for nom, m in masques.items():
        g = evaluer_groupe(y[m], probas[m], prior, majoritaire, np.random.default_rng(GRAINE))
        ref = reference["resultats"][nom]
        # Mêmes lignes, mêmes références : les métriques des références doivent être identiques
        for cle in ("classe_majoritaire", "aleatoire_selon_repartition", "brier_reference_repartition_constante",
                    "repartition_reelle"):
            if g[cle] != ref[cle]:
                raise AssertionError(f"Référence {cle} différente de reference_v1 pour {nom}")
        resultats[nom] = {"v3": g.pop("modele"), "v1": ref["modele"], "classe_majoritaire_nom": majoritaire, **g}
        resultats[nom]["verdicts"] = verdicts(resultats[nom])

    sortie = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reexecution": bool(args.refaire),
        "modele": comparaison["choix"],
        "localisation": artefact["localisation"],
        "calibration": calibration["methode_retenue"],
        "test": {"lignes": int(len(test)), "du": str(test["date_etablissement_dpe"].min()),
                 "au": str(test["date_etablissement_dpe"].max()), "date_coupure": reference["date_coupure"],
                 "identique_a_reference_v1": True},
        "resultats": resultats,
    }
    SORTIE_JSON.write_bytes(json.dumps(sortie, ensure_ascii=False, indent=2).encode("utf-8"))
    SORTIE_MD.write_bytes(rapport(sortie).encode("utf-8"))
    print(phrase(resultats["tous"]))


def rapport(s: dict) -> str:
    t = s["test"]
    l = ["# Modèle v3 : évaluation finale sur le test temporel", "",
         f"Généré par `training/evaluer_v3.py` le {s['genere_le']}" + (" (**réexécution**)" if s["reexecution"] else "") + ".",
         f"Modèle : {s['modele']} ; localisation : {s['localisation']} ; calibration : {s['calibration']}.", "",
         "## Verdict", "", phrase(s["resultats"]["tous"]), "",
         "## Jeu de test", "",
         f"- Exactement le test de `reports/reference_v1.md` : DPE PACA établis après le {t['date_coupure']} "
         f"(du {t['du']} au {t['au']}), mêmes exclusions : **{_n(t['lignes'])} DPE**, étiquette réelle `etiquette_dpe`.",
         "- Vérifié par le script : effectif, exclusions, répartition des classes et métriques des références "
         "identiques à `reference_v1.json`.",
         "- Le test n'a servi à aucun choix (modèle, réglages, calibration : validation du 2026-05-01 au 2026-08-30).",
         "- Probabilités calculées avec le code de l'API (`app/ml/modele_v3.py`), calibration comprise."]
    for nom, titre in GROUPES.items():
        r = s["resultats"][nom]
        l += ["", f"## {titre} ({_n(r['v3']['effectif'])} DPE)", "", phrase(r), "", tableau(r), "",
              "Fiabilité des probabilités du v3 :", "", _fiabilite(r["v3"]["fiabilite"]), "",
              "Matrice de confusion du v3 :", "", _matrice(r["v3"]["matrice_confusion"])]
    return "\n".join(l) + "\n"


if __name__ == "__main__":
    main()
