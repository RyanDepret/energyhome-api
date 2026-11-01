"""Comparaison des modèles v3 sur la validation (jamais sur le test).

Modèles : références (classe majoritaire, répartition), régression logistique multinomiale,
Random Forest (sans puis avec class_weight='balanced'), LightGBM multiclasse, et une approche
ordinale (régression du CEP et des EGES par m², puis seuils officiels de l'étiquette).

Localisation (zone, département ou les deux) : à Brier quasi égal (écart ≤ 0,002), la plus simple.

Règle de choix, fixée avant de regarder les résultats :
  1. éliminer les modèles dont le fichier dépasse TAILLE_MAX_MO ;
  2. retenir le plus petit score de Brier multiclasse sur la validation ;
  3. à moins de 0,002 de Brier près, départager par l'accuracy.

Sorties : reports/comparaison_v3.json, reports/comparaison_v3.md,
          data/modeles_v3/*.joblib (modèles candidats, non commités)

Usage : .venv/Scripts/python.exe -m training.comparer_modeles
"""

from __future__ import annotations

import json
import tempfile
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, SplineTransformer, StandardScaler

from app.ml.features_v3 import CATEGORIELLES, LOCALISATIONS
from app.ml.model import CLASSES_DPE
from training.donnees_v3 import Jeux, charger
from training.etiquettes import _indice_classe, seuils_lot
from training.evaluer import GRAINE, brier_multiclasse, metriques

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_MODELES = RACINE / "data" / "modeles_v3"
SORTIE_JSON = RACINE / "reports" / "comparaison_v3.json"
SORTIE_MD = RACINE / "reports" / "comparaison_v3.md"

TAILLE_MAX_MO = 50
ECART_BRIER_EGALITE = 0.002
N_JOBS = -1

# Recherche d'hyperparamètres LightGBM : petite grille, arrêt anticipé sur la validation
GRILLE_LGBM = [
    {"num_leaves": nl, "learning_rate": lr, "min_child_samples": mcs}
    for nl, lr, mcs in [(31, 0.1, 100), (63, 0.1, 100), (127, 0.1, 100), (255, 0.1, 100),
                        (63, 0.05, 100), (127, 0.05, 100), (63, 0.1, 500), (127, 0.1, 500),
                        (255, 0.05, 500), (511, 0.05, 1000)]
]
GRILLE_RF = [
    {"n_estimators": 100, "min_samples_leaf": 500, "max_features": "sqrt"},
    {"n_estimators": 100, "min_samples_leaf": 200, "max_features": "sqrt"},
    {"n_estimators": 60, "min_samples_leaf": 100, "max_features": 0.5},
]
N_TIRAGES_ORDINAL = 200

# lightgbm 4.7 annonce l'abandon de `eval_set`, mais son remplaçant `eval_X`/`eval_y`
# n'encode pas les étiquettes texte des classifieurs : on garde `eval_set`
warnings.filterwarnings("ignore", message="The argument 'eval_set' is deprecated")


# ── Outils communs ───────────────────────────────────────────────────────────

def taille_mo(objet) -> float:
    """Taille du fichier sérialisé (joblib, compression 3, comme l'artefact final)."""
    with tempfile.TemporaryDirectory() as d:
        chemin = Path(d) / "m.joblib"
        joblib.dump(objet, chemin, compress=3)
        return chemin.stat().st_size / 1e6


def evaluer_probas(y, probas: np.ndarray) -> dict:
    pred = np.asarray(CLASSES_DPE)[probas.argmax(axis=1)]
    m = metriques(y, pred)
    m["brier_multiclasse"] = brier_multiclasse(y, probas)
    del m["matrice_confusion"]
    return m


def probas_7_classes(modele, X) -> np.ndarray:
    p = modele.predict_proba(X)
    classes = [str(c) for c in modele.classes_]
    assert classes == CLASSES_DPE, classes
    return p


# ── Modèles ──────────────────────────────────────────────────────────────────

def preprocesseur_lineaire(colonnes: list[str]) -> ColumnTransformer:
    """Log de la surface en splines, période et catégories en indicatrices."""
    cat = [c for c in colonnes if c in CATEGORIELLES] + ["periode"]
    return ColumnTransformer([
        ("surface", make_pipeline(FunctionTransformer(np.log), SplineTransformer(n_knots=6, degree=3),
                                  StandardScaler()), ["surface"]),
        ("categories", OneHotEncoder(handle_unknown="ignore"), cat),
    ])


def preprocesseur_arbres(colonnes: list[str]) -> ColumnTransformer:
    cat = [c for c in colonnes if c in CATEGORIELLES]
    return ColumnTransformer([
        ("num", "passthrough", ["surface", "periode"]),
        ("categories", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
    ])


def entrainer_lgbm(X, y, Xv, yv, params: dict, max_tours: int = 3000):
    modele = lgb.LGBMClassifier(objective="multiclass", n_estimators=max_tours, subsample=0.8, subsample_freq=1,
                                colsample_bytree=1.0, random_state=GRAINE, n_jobs=N_JOBS, verbose=-1, **params)
    modele.fit(X, y, eval_set=[(Xv, yv)], eval_metric="multi_logloss",
               callbacks=[lgb.early_stopping(50, verbose=False)])
    return modele


class ModeleOrdinal:
    """Régression du log CEP et du log EGES par m², puis seuils officiels de l'étiquette.

    Les probabilités viennent de résidus (log CEP, log EGES) tirés conjointement sur une
    partie de l'entraînement mise de côté : chaque tirage donne une étiquette par les seuils
    de l'arrêté (surface comprise ; altitude inconnue, donc seuils hors altitude).
    """

    def __init__(self, params: dict, n_tirages: int = N_TIRAGES_ORDINAL):
        self.params, self.n_tirages = params, n_tirages
        self.classes_ = np.asarray(CLASSES_DPE)

    def fit(self, X, cep, eges, Xv=None, cepv=None, egesv=None):
        rng = np.random.default_rng(GRAINE)
        garde = rng.random(len(X)) < 0.05
        self.modeles = {}
        residus = []
        for nom, cible, cible_v in (("cep", cep, cepv), ("eges", eges, egesv)):
            yl = np.log1p(np.asarray(cible, dtype=float))
            m = lgb.LGBMRegressor(n_estimators=3000, random_state=GRAINE, n_jobs=N_JOBS, verbose=-1,
                                  subsample=0.8, subsample_freq=1, **self.params)
            m.fit(X[~garde], yl[~garde], eval_set=[(X[garde], yl[garde])],
                  callbacks=[lgb.early_stopping(50, verbose=False)])
            self.modeles[nom] = m
            residus.append(yl[garde] - m.predict(X[garde]))
        r = np.column_stack(residus)
        self.residus = r[rng.choice(len(r), size=self.n_tirages, replace=False)]
        return self

    def predict_proba(self, X, lot: int = 5000) -> np.ndarray:
        return np.vstack([self._predict_proba(X.iloc[i:i + lot]) for i in range(0, len(X), lot)])

    def _predict_proba(self, X) -> np.ndarray:
        lc = self.modeles["cep"].predict(X)[:, None] + self.residus[None, :, 0]
        lg = self.modeles["eges"].predict(X)[:, None] + self.residus[None, :, 1]
        cep_s, eges_s = seuils_lot(pd.DataFrame({"surface_habitable_logement": X["surface"].to_numpy()}))
        n, k = lc.shape
        ic = _indice_classe(np.expm1(lc).ravel(), np.repeat(cep_s, k, axis=0)).reshape(n, k)
        ig = _indice_classe(np.expm1(lg).ravel(), np.repeat(eges_s, k, axis=0)).reshape(n, k)
        indice = np.maximum(ic, ig)
        return np.stack([(indice == i).mean(axis=1) for i in range(len(CLASSES_DPE))], axis=1)


# ── Programme ────────────────────────────────────────────────────────────────

def chrono(f):
    t0 = time.perf_counter()
    r = f()
    return r, time.perf_counter() - t0


def resultat(nom, famille, y_val, probas, secondes, objet, params=None, extra=None) -> dict:
    r = {"nom": nom, "famille": famille, "params": params or {},
         "secondes_entrainement": round(secondes, 1),
         "taille_mo": round(taille_mo(objet), 2) if objet is not None else 0.0,
         "validation": evaluer_probas(y_val, probas)}
    if extra:
        r.update(extra)
    print(f"{nom:45s} Brier {r['validation']['brier_multiclasse']:.4f}  acc {r['validation']['accuracy']:.4f}  "
          f"{r['secondes_entrainement']:7.1f} s  {r['taille_mo']:7.2f} Mo", flush=True)
    return r


def choisir(resultats: list[dict]) -> dict:
    admissibles = [r for r in resultats if r["famille"] not in ("reference",) and r["taille_mo"] <= TAILLE_MAX_MO]
    meilleur_brier = min(r["validation"]["brier_multiclasse"] for r in admissibles)
    proches = [r for r in admissibles if r["validation"]["brier_multiclasse"] <= meilleur_brier + ECART_BRIER_EGALITE]
    return max(proches, key=lambda r: r["validation"]["accuracy"])


def main() -> None:
    global GRILLE_LGBM, GRILLE_RF, SORTIE_JSON, SORTIE_MD, DOSSIER_MODELES
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--echantillon", type=int, default=None, help="essai rapide : n lignes d'entraînement")
    args = parser.parse_args()
    DOSSIER_MODELES.mkdir(parents=True, exist_ok=True)
    jeux: Jeux = charger()
    if args.echantillon:
        idx = jeux.entrees["entrainement"].sample(args.echantillon, random_state=GRAINE).index
        jeux.entrees["entrainement"] = jeux.entrees["entrainement"].loc[idx]
        jeux.brut["entrainement"] = jeux.brut["entrainement"].loc[idx]
        jeux.y["entrainement"] = jeux.brut["entrainement"]["cible"].to_numpy().astype(str)
        GRILLE_LGBM, GRILLE_RF = GRILLE_LGBM[:2], GRILLE_RF[:1]
        tmp = Path(tempfile.mkdtemp())
        SORTIE_JSON, SORTIE_MD, DOSSIER_MODELES = tmp / "c.json", tmp / "c.md", tmp
    y, yv = jeux.y["entrainement"], jeux.y["validation"]
    res: list[dict] = []

    # 1. Références (apprises sur l'entraînement)
    prior = np.array([(y == c).mean() for c in CLASSES_DPE])
    majoritaire = CLASSES_DPE[int(prior.argmax())]
    p_maj = np.zeros((len(yv), 7)); p_maj[:, CLASSES_DPE.index(majoritaire)] = 1
    res.append(resultat(f"Classe majoritaire ({majoritaire})", "reference", yv, p_maj, 0, None))
    r_rep = resultat("Répartition des classes (probabilités constantes)", "reference", yv,
                     np.tile(prior, (len(yv), 1)), 0, None)
    tirage = np.random.default_rng(GRAINE).choice(CLASSES_DPE, size=len(yv), p=prior)
    r_rep["validation_tirage_aleatoire"] = {k: v for k, v in metriques(yv, tirage).items() if k != "matrice_confusion"}
    res.append(r_rep)

    # 2. Localisation : zone, département ou les deux (LightGBM, réglage de base)
    base = GRILLE_LGBM[1]
    localisations = {}
    for loc in LOCALISATIONS:
        X, Xv = jeux.X("entrainement", loc), jeux.X("validation", loc)
        m, s = chrono(lambda: entrainer_lgbm(X, y, Xv, yv, base))
        r = resultat(f"LightGBM base, localisation = {loc}", "localisation", yv, probas_7_classes(m, Xv), s, m,
                     base, {"localisation": loc, "meilleure_iteration": int(m.best_iteration_)})
        localisations[loc] = r
        res.append(r)
    # La zone climatique est une fonction du département (table de l'API) : à Brier quasi égal
    # (écart ≤ ECART_BRIER_EGALITE), on garde la localisation qui a le moins de variables
    meilleur = min(r["validation"]["brier_multiclasse"] for r in localisations.values())
    loc = min((k for k, r in localisations.items() if r["validation"]["brier_multiclasse"] <= meilleur + ECART_BRIER_EGALITE),
              key=lambda k: (len(LOCALISATIONS[k]), localisations[k]["validation"]["brier_multiclasse"]))
    print("Localisation retenue :", loc, flush=True)
    X, Xv = jeux.X("entrainement", loc), jeux.X("validation", loc)
    colonnes = list(X.columns)

    # 3. Régression logistique multinomiale
    lr = make_pipeline(preprocesseur_lineaire(colonnes), LogisticRegression(max_iter=500, C=1.0))
    _, s = chrono(lambda: lr.fit(X, y))
    res.append(resultat("Régression logistique multinomiale", "logistique", yv, probas_7_classes(lr, Xv), s, lr,
                        {"C": 1.0, "surface": "splines de log(surface), 6 nœuds"}))

    # 4. Random Forest, sans puis avec class_weight='balanced'
    for params in GRILLE_RF:
        for poids in (None, "balanced"):
            rf = make_pipeline(preprocesseur_arbres(colonnes),
                               RandomForestClassifier(class_weight=poids, random_state=GRAINE, n_jobs=N_JOBS, **params))
            _, s = chrono(lambda: rf.fit(X, y))
            nom = f"Random Forest {params['n_estimators']} arbres, feuilles ≥ {params['min_samples_leaf']}" + (
                ", balanced" if poids else "")
            res.append(resultat(nom, "random_forest", yv, probas_7_classes(rf, Xv), s, rf,
                                {**params, "class_weight": poids}))
            del rf

    # 5. LightGBM multiclasse : grille
    meilleur_lgbm, meilleur_brier = None, np.inf
    for params in GRILLE_LGBM:
        m, s = chrono(lambda: entrainer_lgbm(X, y, Xv, yv, params))
        r = resultat(f"LightGBM {params}", "lightgbm", yv, probas_7_classes(m, Xv), s, m, params,
                     {"meilleure_iteration": int(m.best_iteration_)})
        res.append(r)
        if r["validation"]["brier_multiclasse"] < meilleur_brier:
            meilleur_brier, meilleur_lgbm = r["validation"]["brier_multiclasse"], m
    joblib.dump(meilleur_lgbm, DOSSIER_MODELES / "lightgbm.joblib", compress=3)

    # 6. Approche ordinale : régression CEP et EGES puis seuils
    brut = jeux.brut["entrainement"]
    for params in ({"num_leaves": 127, "learning_rate": 0.1, "min_child_samples": 100},):
        om = ModeleOrdinal(params)
        _, s = chrono(lambda: om.fit(X, brut["conso_5_usages_par_m2_ep"].to_numpy(),
                                     brut["emission_ges_5_usages_par_m2"].to_numpy()))
        res.append(resultat("Ordinal : régression CEP et EGES puis seuils", "ordinal", yv, om.predict_proba(Xv), s, om,
                            params))

    choix = choisir(res)
    sortie = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "regle_de_choix": {"taille_max_mo": TAILLE_MAX_MO, "ecart_brier_egalite": ECART_BRIER_EGALITE,
                           "texte": "taille ≤ max, puis plus petit Brier, puis accuracy à égalité de Brier"},
        "localisation_retenue": loc,
        "colonnes": colonnes,
        "donnees": {k: jeux.bilan["jeux"][k]["lignes"] for k in ("entrainement", "validation")},
        "resultats": res,
        "choix": choix["nom"],
    }
    SORTIE_JSON.write_bytes(json.dumps(sortie, ensure_ascii=False, indent=2).encode("utf-8"))
    SORTIE_MD.write_bytes(rapport(sortie).encode("utf-8"))
    print("Choix :", choix["nom"])


def _p(x) -> str:
    return f"{100 * x:.1f} %"


def rapport(s: dict) -> str:
    lignes = [
        "# Comparaison des modèles v3 (validation)", "",
        f"Généré par `training/comparer_modeles.py` le {s['genere_le']}.", "",
        f"Entraînement : {s['donnees']['entrainement']:,} DPE établis avant le 2026-05-01 ; validation : "
        f"{s['donnees']['validation']:,} DPE du 2026-05-01 au 2026-08-30. Le test n'est pas utilisé ici.".replace(",", " "),
        "", f"Règle de choix fixée à l'avance : {s['regle_de_choix']['texte']} "
        f"(taille max {s['regle_de_choix']['taille_max_mo']} Mo, égalité si écart de Brier ≤ "
        f"{s['regle_de_choix']['ecart_brier_egalite']}).", "",
        f"Localisation retenue : **{s['localisation_retenue']}** (variables : {', '.join(s['colonnes'])}).", "",
        f"**Modèle retenu : {s['choix']}**", "",
        "| Modèle | Accuracy | F1 macro | À une classe près | Brier | Entraînement | Fichier |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in s["resultats"]:
        v = r["validation"]
        lignes.append(f"| {r['nom']} | {_p(v['accuracy'])} | {_p(v['f1_macro'])} | {_p(v['accuracy_a_une_classe_pres'])} | "
                      f"{v['brier_multiclasse']:.4f} | {r['secondes_entrainement']:.0f} s | {r['taille_mo']:.1f} Mo |")
    rep = next(r for r in s["resultats"] if "validation_tirage_aleatoire" in r)
    t = rep["validation_tirage_aleatoire"]
    lignes += ["", f"Tirage aléatoire selon la répartition (graine {GRAINE}) : accuracy {_p(t['accuracy'])}, "
               f"F1 macro {_p(t['f1_macro'])}, à une classe près {_p(t['accuracy_a_une_classe_pres'])}.", "",
               "Notes :",
               "- Les LightGBM utilisent l'arrêt anticipé sur la validation (50 tours sans progrès de la log-loss) : "
               "leurs scores de validation sont légèrement optimistes ; le test reste intact.",
               "- Localisation : la règle « à Brier quasi égal, la plus simple » a été ajoutée après une première "
               "exécution où « département + zone » devançait « département » de 0,0001 de Brier ; la zone étant une "
               "fonction du département, cet écart est du bruit. Les deux autres règles n'ont pas changé.",
               "- Taille : fichier joblib compressé (niveau 3), comme l'artefact final.",
               "- Temps mesurés sur un PC portable, 16 cœurs logiques.",
               "- Approche ordinale : altitude inconnue à la saisie, donc seuils hors altitude ; probabilités par "
               f"{N_TIRAGES_ORDINAL} tirages conjoints de résidus mis de côté sur l'entraînement."]
    return "\n".join(lignes) + "\n"


if __name__ == "__main__":
    main()
