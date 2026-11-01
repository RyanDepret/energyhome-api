"""Mesure honnête du modèle actuel sur un test temporel PACA, face à des références simples.

Entrée  : data/dpe_paca.parquet (training/nettoyer.py)
Sorties : reports/reference_v1.json (tous les chiffres) et reports/reference_v1.md

Le modèle est chargé et les features construites avec le code de l'API (app/ml/), à partir
des mêmes entrées que /predict : période, type de bâtiment, chauffage, surface et zone
climatique déduite du département (comme en production).

Usage : .venv/Scripts/python.exe -m training.evaluer
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from app.core.config import settings
from app.ml.features import SURFACE_COLUMN, build_features, categorical_columns
from app.ml.model import CLASSES_DPE, get_columns, get_model, get_zones
from app.schemas.predict import CHAUFFAGE_LABELS, PERIODE_LABELS, TYPE_BATIMENT_LABELS

RACINE = Path(__file__).resolve().parent.parent
ENTREE = RACINE / "data" / "dpe_paca.parquet"
EXTRACTION = RACINE / "data" / "extraction_r93.json"
SORTIE_JSON = RACINE / "reports" / "reference_v1.json"
SORTIE_MD = RACINE / "reports" / "reference_v1.md"
CHEMIN_MODELE_GIT = "artifacts/modele_dpe_v2.pkl"

DATE_COEFFICIENT_1_9 = "2026-01-01"  # DPE établis depuis cette date : coefficient électricité 1,9 (au lieu de 2,3)
GRAINE = 42

# Ajoutée après la mesure du coefficient réellement publié (training/valider_etiquettes.py)
NOTE_CORRECTIVE = """## Note corrective du 2026-11-01

La section suivante attribue une partie des erreurs au fait que le modèle aurait appris des étiquettes
calculées avec le coefficient 2,3. Une mesure faite après ce rapport (`training/valider_etiquettes.py`,
`reports/validation_etiquettes.md`) montre que le jeu ADEME extrait le 2026-10-31 publie **tous** les DPE
en 1,9, y compris ceux établis avant 2026 : pour les DPE dont la seule énergie est l'électricité, le rapport
énergie primaire / énergie finale a une médiane de 1,906 avant 2026 (549 768 DPE) et de 1,902 depuis
(95 565 DPE). Cette explication ne vaut donc pas pour les données actuelles ; elle vaut peut-être pour
l'extraction de 2025 qui a servi à entraîner le modèle, ce qui ne peut plus être vérifié.
Les chiffres de ce rapport ne changent pas.

"""

# Libellés ADEME → valeurs d'Enum de l'API (mêmes tables que /predict)
PERIODE_ADEME = {label: p for p, label in PERIODE_LABELS.items()}
TYPE_ADEME = {label: t for t, label in TYPE_BATIMENT_LABELS.items()}
CHAUFFAGE_ADEME = {label: c for c, label in CHAUFFAGE_LABELS.items()}


# ── Date d'entraînement du modèle, lue dans Git ─────────────────────────────

def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=RACINE, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout.strip()


def commits_du_modele() -> dict:
    """Dernier commit qui a touché le .pkl, et commit qui a produit son contenu actuel.

    Un déplacement de fichier apparaît dans `git log` sans changer le contenu : le commit de
    production est le plus ancien commit dont le blob est identique au blob actuel.
    """
    blob_actuel = _git("rev-parse", f"HEAD:{CHEMIN_MODELE_GIT}")
    sortie = _git("log", "--follow", "--name-only", "--format=@@%H|%h|%cs|%s", "--", CHEMIN_MODELE_GIT)
    commits = []
    for bloc in sortie.split("@@")[1:]:
        lignes = [x for x in bloc.splitlines() if x.strip()]
        complet, court, date, sujet = lignes[0].split("|", 3)
        chemin = lignes[1]
        commits.append({"commit": court, "date": date, "sujet": sujet, "chemin": chemin,
                        "blob": _git("rev-parse", f"{complet}:{chemin}")})
    meme_contenu = [c for c in commits if c["blob"] == blob_actuel]
    return {"blob_actuel": blob_actuel, "dernier_commit": commits[0], "commit_production": meme_contenu[-1],
            "historique": commits}


# ── Features : même code que l'API ───────────────────────────────────────────

def preparer_entrees(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Convertit les libellés ADEME en entrées de l'API ; exclut (en comptant) ce que l'API refuserait."""
    zones = get_zones()
    entrees = pd.DataFrame({
        "periode": df["periode_construction"].map(PERIODE_ADEME),
        "type_batiment": df["type_batiment"].map(TYPE_ADEME),
        "chauffage": df["type_energie_principale_chauffage"].map(CHAUFFAGE_ADEME),
        "zone_climatique_api": df["code_departement_ban"].map(zones),
    }, index=df.index)
    exclusions = {
        "periode_inconnue": int(entrees["periode"].isna().sum()),
        "type_batiment_inconnu": int(entrees["type_batiment"].isna().sum()),
        "chauffage_inconnu": int(entrees["chauffage"].isna().sum()),
        "departement_sans_zone": int(entrees["zone_climatique_api"].isna().sum()),
    }
    valide = entrees.notna().all(axis=1)
    exclusions["total_lignes_exclues"] = int((~valide).sum())
    return entrees[valide], exclusions


def features_en_lot(surfaces, entrees: pd.DataFrame, colonnes: list[str]) -> pd.DataFrame:
    """Matrice de features construite avec `categorical_columns` de l'API (identique à build_features)."""
    index = {c: i for i, c in enumerate(colonnes)}
    matrice = np.zeros((len(entrees), len(colonnes)))
    matrice[:, index[SURFACE_COLUMN]] = np.asarray(surfaces, dtype=float)
    for ligne, (p, t, c, z) in enumerate(entrees[["periode", "type_batiment", "chauffage",
                                                  "zone_climatique_api"]].itertuples(index=False)):
        for colonne in categorical_columns(p, t, c, z).values():
            matrice[ligne, index[colonne]] = 1  # KeyError si la colonne n'existe pas : jamais ignoré
    return pd.DataFrame(matrice, columns=colonnes)


def verifier_contre_build_features(surfaces, entrees, X: pd.DataFrame, colonnes, n=500) -> int:
    """Compare un échantillon de lignes à build_features (le code exact de /predict)."""
    rng = np.random.default_rng(GRAINE)
    lignes = rng.choice(len(entrees), size=min(n, len(entrees)), replace=False)
    for i in lignes:
        e = entrees.iloc[i]
        attendu = build_features(float(np.asarray(surfaces)[i]), e["periode"], e["type_batiment"],
                                 e["chauffage"], e["zone_climatique_api"], colonnes)
        if not np.array_equal(attendu.to_numpy(dtype=float)[0], X.iloc[i].to_numpy()):
            raise AssertionError(f"Features en lot différentes de build_features à la ligne {i}")
    return len(lignes)


# ── Métriques ────────────────────────────────────────────────────────────────

def accuracy_a_une_classe_pres(y_vrai, y_pred) -> float:
    """Part des prédictions à au plus une classe de l'étiquette réelle (A–G ordonnées)."""
    rang = {c: i for i, c in enumerate(CLASSES_DPE)}
    vrai = np.array([rang[c] for c in y_vrai])
    pred = np.array([rang[c] for c in y_pred])
    return float(np.mean(np.abs(vrai - pred) <= 1)) if len(vrai) else float("nan")


def brier_multiclasse(y_vrai, probas: np.ndarray) -> float:
    """Moyenne sur les DPE de la somme sur les 7 classes de (p_k − 1[classe = k])²."""
    cible = np.zeros_like(probas)
    rang = {c: i for i, c in enumerate(CLASSES_DPE)}
    cible[np.arange(len(probas)), [rang[c] for c in y_vrai]] = 1
    return float(np.mean(np.sum((probas - cible) ** 2, axis=1)))


def fiabilite(y_vrai, probas: np.ndarray) -> list[dict]:
    """Probabilité annoncée pour la classe prédite, par tranches de 10 %, → taux de bonnes réponses."""
    confiance = probas.max(axis=1)
    pred = np.array(CLASSES_DPE)[probas.argmax(axis=1)]
    juste = pred == np.asarray(y_vrai)
    tranches = np.minimum((confiance * 10).astype(int), 9)
    resultat = []
    for t in range(10):
        masque = tranches == t
        resultat.append({
            "tranche": f"{t * 10}–{(t + 1) * 10} %",
            "effectif": int(masque.sum()),
            "probabilite_moyenne_annoncee": float(confiance[masque].mean()) if masque.any() else None,
            "taux_bonnes_reponses": float(juste[masque].mean()) if masque.any() else None,
        })
    return resultat


def metriques(y_vrai, y_pred) -> dict:
    y_vrai, y_pred = list(y_vrai), list(y_pred)
    f1 = f1_score(y_vrai, y_pred, labels=CLASSES_DPE, average=None, zero_division=0)
    return {
        "effectif": len(y_vrai),
        "accuracy": float(accuracy_score(y_vrai, y_pred)),
        "f1_macro": float(f1_score(y_vrai, y_pred, labels=CLASSES_DPE, average="macro", zero_division=0)),
        "accuracy_a_une_classe_pres": accuracy_a_une_classe_pres(y_vrai, y_pred),
        "f1_par_classe": {c: float(v) for c, v in zip(CLASSES_DPE, f1)},
        "matrice_confusion": confusion_matrix(y_vrai, y_pred, labels=CLASSES_DPE).tolist(),
    }


def repartition(serie: pd.Series) -> dict:
    effectifs = serie.value_counts().reindex(CLASSES_DPE, fill_value=0)
    total = int(effectifs.sum())
    return {"total": total, "effectifs": {c: int(n) for c, n in effectifs.items()},
            "pourcentages": {c: (100 * n / total if total else None) for c, n in effectifs.items()}}


def est_electrique(df: pd.DataFrame) -> pd.Series:
    return df["type_energie_principale_chauffage"].fillna("").str.startswith("Électricité")


def evaluer_groupe(y, probas_modele, prior: np.ndarray, classe_majoritaire: str, rng) -> dict:
    y = np.asarray(y)
    pred_modele = np.array(CLASSES_DPE)[probas_modele.argmax(axis=1)]
    pred_majoritaire = np.full(len(y), classe_majoritaire)
    pred_aleatoire = rng.choice(CLASSES_DPE, size=len(y), p=prior)
    probas_prior = np.tile(prior, (len(y), 1))
    modele = metriques(y, pred_modele)
    modele["brier_multiclasse"] = brier_multiclasse(y, probas_modele)
    modele["fiabilite"] = fiabilite(y, probas_modele)
    return {
        "modele": modele,
        "classe_majoritaire": metriques(y, pred_majoritaire),
        "aleatoire_selon_repartition": metriques(y, pred_aleatoire),
        "brier_reference_repartition_constante": brier_multiclasse(y, probas_prior),
        "repartition_reelle": repartition(pd.Series(y)),
    }


# ── Programme principal ─────────────────────────────────────────────────────

def evaluer(df: pd.DataFrame, date_coupure: str) -> dict:
    df = df.reset_index(drop=True)
    avant = df[df["date_etablissement_dpe"] <= date_coupure]
    test_brut = df[df["date_etablissement_dpe"] > date_coupure]

    # Références construites sans regarder le test : répartition PACA connue à la date d'entraînement
    rep_avant = repartition(avant["etiquette_dpe"])
    prior = np.array([rep_avant["effectifs"][c] for c in CLASSES_DPE], dtype=float)
    prior /= prior.sum()
    classe_majoritaire = CLASSES_DPE[int(prior.argmax())]

    entrees, exclusions = preparer_entrees(test_brut)
    test = test_brut.loc[entrees.index]
    if test.empty:
        raise ValueError(f"Aucun DPE évaluable établi après le {date_coupure} : test temporel vide.")
    colonnes = get_columns()
    X = features_en_lot(test[SURFACE_COLUMN], entrees, colonnes)
    lignes_verifiees = verifier_contre_build_features(test[SURFACE_COLUMN].to_numpy(), entrees, X, colonnes)

    modele = get_model()
    if list(modele.classes_) != CLASSES_DPE:
        raise AssertionError(f"Classes du modèle inattendues : {modele.classes_}")
    probas = modele.predict_proba(X)

    elec = est_electrique(test).to_numpy()
    groupes = {"tous": np.ones(len(test), dtype=bool), "chauffage_electrique": elec, "autres_chauffages": ~elec}
    y = test["etiquette_dpe"].to_numpy()
    resultats = {}
    for nom, masque in groupes.items():
        resultats[nom] = evaluer_groupe(y[masque], probas[masque], prior, classe_majoritaire,
                                        np.random.default_rng(GRAINE))

    # Coefficient électricité 1,9 dans le test
    depuis_2026 = test["date_etablissement_dpe"] >= DATE_COEFFICIENT_1_9
    coefficient = {
        "test_total": len(test),
        "etablis_depuis_2026_01_01": int(depuis_2026.sum()),
        "dont_chauffage_electrique": int((depuis_2026 & est_electrique(test)).sum()),
        "dont_autres_chauffages": int((depuis_2026 & ~est_electrique(test)).sum()),
    }

    # Comparaison descriptive PACA avant / depuis le 1er janvier 2026 (tout le jeu nettoyé)
    avant_2026 = df["date_etablissement_dpe"] < DATE_COEFFICIENT_1_9
    elec_tous = est_electrique(df)
    comparaison = {}
    for nom_groupe, masque_groupe in [("chauffage_electrique", elec_tous), ("autres_chauffages", ~elec_tous)]:
        comparaison[nom_groupe] = {
            "avant_2026": repartition(df.loc[masque_groupe & avant_2026, "etiquette_dpe"]),
            "depuis_2026": repartition(df.loc[masque_groupe & ~avant_2026, "etiquette_dpe"]),
        }

    zones_differentes = int((test["zone_climatique"].to_numpy() != entrees["zone_climatique_api"].to_numpy()).sum())

    return {
        "date_coupure": date_coupure,
        "periode_test": {"min": test["date_etablissement_dpe"].min(), "max": test["date_etablissement_dpe"].max()},
        "jeu_nettoye": len(df),
        "avant_coupure": len(avant),
        "test_brut": len(test_brut),
        "exclusions_test": exclusions,
        "test_evalue": len(test),
        "lignes_verifiees_contre_build_features": lignes_verifiees,
        "zone_dataset_differente_de_zone_api": zones_differentes,
        "references": {"classe_majoritaire": classe_majoritaire, "repartition_avant_coupure": rep_avant,
                       "graine_tirage_aleatoire": GRAINE},
        "resultats": resultats,
        "coefficient_electricite_1_9": coefficient,
        "comparaison_avant_depuis_2026": comparaison,
    }


# ── Rapport Markdown ────────────────────────────────────────────────────────

def _n(x) -> str:
    return f"{x:,}".replace(",", " ")


def _p(x) -> str:
    return "—" if x is None else f"{100 * x:.1f} %"


def _tableau_comparatif(r: dict) -> str:
    lignes = ["| | Modèle actuel | Classe majoritaire | Aléatoire selon la répartition |", "|---|---:|---:|---:|"]
    for cle, libelle in [("accuracy", "Accuracy"), ("f1_macro", "F1 macro"),
                         ("accuracy_a_une_classe_pres", "Accuracy à une classe près")]:
        lignes.append(f"| {libelle} | {_p(r['modele'][cle])} | {_p(r['classe_majoritaire'][cle])} | "
                      f"{_p(r['aleatoire_selon_repartition'][cle])} |")
    for c in CLASSES_DPE:
        lignes.append(f"| F1 classe {c} | {r['modele']['f1_par_classe'][c]:.3f} | "
                      f"{r['classe_majoritaire']['f1_par_classe'][c]:.3f} | "
                      f"{r['aleatoire_selon_repartition']['f1_par_classe'][c]:.3f} |")
    return "\n".join(lignes)


def _matrice(m: list[list[int]]) -> str:
    lignes = ["| Réel ↓ / Prédit → | " + " | ".join(CLASSES_DPE) + " |", "|---|" + "---:|" * 7]
    for c, ligne in zip(CLASSES_DPE, m):
        lignes.append(f"| **{c}** | " + " | ".join(_n(v) for v in ligne) + " |")
    return "\n".join(lignes)


def _fiabilite(f: list[dict]) -> str:
    lignes = ["| Probabilité annoncée | Effectif | Probabilité moyenne | Taux de bonnes réponses |",
              "|---|---:|---:|---:|"]
    for t in f:
        lignes.append(f"| {t['tranche']} | {_n(t['effectif'])} | {_p(t['probabilite_moyenne_annoncee'])} | "
                      f"{_p(t['taux_bonnes_reponses'])} |")
    return "\n".join(lignes)


def _repartitions(colonnes: dict[str, dict]) -> str:
    entete = "| Classe | " + " | ".join(colonnes) + " |"
    lignes = [entete, "|---|" + "---:|" * len(colonnes)]
    for c in CLASSES_DPE:
        cellules = [f"{_n(r['effectifs'][c])} ({r['pourcentages'][c]:.1f} %)" if r["total"] else "—"
                    for r in colonnes.values()]
        lignes.append(f"| {c} | " + " | ".join(cellules) + " |")
    lignes.append("| Total | " + " | ".join(_n(r["total"]) for r in colonnes.values()) + " |")
    return "\n".join(lignes)


def phrase_verdict(r: dict) -> str:
    m, ref = r["modele"], r["classe_majoritaire"]
    verbe = "bat" if m["accuracy"] > ref["accuracy"] else "ne bat pas"
    return (f"**Le modèle actuel {verbe} la référence « classe majoritaire » en accuracy** "
            f"({_p(m['accuracy'])} contre {_p(ref['accuracy'])} sur le test temporel).")


def rapport(res: dict, git: dict, extraction: dict) -> str:
    tous = res["resultats"]["tous"]
    ex = res["exclusions_test"]
    co = res["coefficient_electricite_1_9"]
    prod, dernier = git["commit_production"], git["dernier_commit"]
    sections_groupes = []
    for nom, titre in [("tous", "Tous les logements"), ("chauffage_electrique", "Chauffage principal électrique"),
                       ("autres_chauffages", "Autres chauffages")]:
        r = res["resultats"][nom]
        sections_groupes.append(f"""### {titre} ({_n(r['modele']['effectif'])} DPE)

{phrase_verdict(r)}

{_tableau_comparatif(r)}

Calibration du modèle : score de Brier multiclasse **{r['modele']['brier_multiclasse']:.4f}**
(référence « répartition constante » : {r['brier_reference_repartition_constante']:.4f} ; plus bas = mieux).

{_fiabilite(r['modele']['fiabilite'])}

Matrice de confusion du modèle :

{_matrice(r['modele']['matrice_confusion'])}
""")
    comp = res["comparaison_avant_depuis_2026"]
    return f"""# Mesure de référence du modèle actuel (v1)

Généré par `training/evaluer.py` le {datetime.now(timezone.utc).isoformat(timespec='seconds')}.
Modèle : `{CHEMIN_MODELE_GIT}` (`model_version` = `{settings.model_version}`), chargé via `app/ml/`.
Données : `data/dpe_paca.parquet`, issu de l'extraction du {extraction['debut_extraction']}
(SHA-256 du brut `{extraction['sha256']}`).

## Verdict

{phrase_verdict(tous)}

## Jeu de test temporel

- Date d'entraînement retenue : **{res['date_coupure']}**, date du commit `{prod['commit']}` (« {prod['sujet']} »)
  qui a produit le contenu actuel du modèle (blob `{git['blob_actuel'][:7]}`).
  Le dernier commit qui a touché le fichier, `{dernier['commit']}` du {dernier['date']} (« {dernier['sujet']} »),
  n'a pas changé son contenu (même blob) : ce n'est pas une date d'entraînement.
- Test : DPE PACA nettoyés établis **après** le {res['date_coupure']} : {_n(res['test_brut'])} DPE
  (du {res['periode_test']['min']} au {res['periode_test']['max']}).
- Exclus car refusés par l'API : {_n(ex['total_lignes_exclues'])}
  (période inconnue {_n(ex['periode_inconnue'])}, type de bâtiment inconnu {_n(ex['type_batiment_inconnu'])},
  chauffage inconnu {_n(ex['chauffage_inconnu'])}, département sans zone {_n(ex['departement_sans_zone'])}).
- **Évalués : {_n(res['test_evalue'])} DPE.**
- Features construites avec `categorical_columns` de l'API ; {_n(res['lignes_verifiees_contre_build_features'])}
  lignes tirées au hasard vérifiées identiques à `build_features` (code exact de `/predict`).
- Zone climatique : comme en production, elle est déduite du département ; elle diffère de la zone indiquée
  dans le DPE pour {_n(res['zone_dataset_differente_de_zone_api'])} DPE du test.

Références à battre, construites **sans regarder le test**, à partir des {_n(res['avant_coupure'])} DPE PACA
établis jusqu'au {res['date_coupure']} :
- « toujours la classe majoritaire » : classe **{res['references']['classe_majoritaire']}** ;
- « tirage aléatoire selon la répartition réelle » : tirage selon cette répartition (graine {res['references']['graine_tirage_aleatoire']}).

{NOTE_CORRECTIVE}## Attention : coefficient électricité 1,9

Les DPE établis depuis le 1er janvier 2026 utilisent un coefficient de conversion de l'électricité en énergie
primaire de 1,9 (au lieu de 2,3). Le modèle a appris sur des étiquettes majoritairement calculées en 2,3.

- DPE du test établis depuis le 1er janvier 2026 : **{_n(co['etablis_depuis_2026_01_01'])} sur {_n(co['test_total'])}**
  - dont chauffage principal électrique : {_n(co['dont_chauffage_electrique'])}
  - dont autres chauffages : {_n(co['dont_autres_chauffages'])}

Les résultats ci-dessous mélangent donc les erreurs propres au modèle et l'effet de ce changement de calcul.

Répartition des classes en PACA (jeu nettoyé complet) avant et depuis le 1er janvier 2026 :

{_repartitions({
    'Électrique avant 2026': comp['chauffage_electrique']['avant_2026'],
    'Électrique depuis 2026': comp['chauffage_electrique']['depuis_2026'],
    'Autres avant 2026': comp['autres_chauffages']['avant_2026'],
    'Autres depuis 2026': comp['autres_chauffages']['depuis_2026'],
})}

Répartition réelle du test comparée à celle utilisée par les références :

{_repartitions({'Test temporel': tous['repartition_reelle'], 'Avant coupure (références)': res['references']['repartition_avant_coupure']})}

## Résultats

{chr(10).join(sections_groupes)}
"""


def main() -> None:
    git = commits_du_modele()
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    df = pd.read_parquet(ENTREE)
    res = evaluer(df, git["commit_production"]["date"])
    res["git_modele"] = git
    res["extraction"] = {k: extraction[k] for k in ("debut_extraction", "lignes", "sha256")}
    SORTIE_JSON.parent.mkdir(parents=True, exist_ok=True)
    SORTIE_JSON.write_bytes(json.dumps(res, ensure_ascii=False, indent=2).encode("utf-8"))
    SORTIE_MD.write_bytes(rapport(res, git, extraction).encode("utf-8"))
    print(phrase_verdict(res["resultats"]["tous"]))


if __name__ == "__main__":
    main()
