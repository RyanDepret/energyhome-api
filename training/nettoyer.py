"""Nettoyage de l'extraction ADEME PACA.

Entrée  : data/dpe_r93_brut.parquet (training/telecharger_dpe.py --region 93)
Sorties : data/dpe_paca.parquet et reports/nettoyage.md (chaque étape chiffrée)

Usage : .venv/Scripts/python.exe -m training.nettoyer
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.ml.features import CATEGORICAL_PREFIXES, SURFACE_COLUMN
from app.ml.model import CLASSES_DPE, get_columns

RACINE = Path(__file__).resolve().parent.parent
ENTREE = RACINE / "data" / "dpe_r93_brut.parquet"
EXTRACTION = RACINE / "data" / "extraction_r93.json"
SORTIE = RACINE / "data" / "dpe_paca.parquet"
RAPPORT = RACINE / "reports" / "nettoyage.md"

SURFACE_MIN = 9  # m², mêmes bornes que la validation de /predict
SURFACE_MAX = 1000

# Colonnes ADEME des variables catégorielles du modèle (préfixe One-Hot sans le "_" final)
VARIABLES_CATEGORIELLES = [prefixe[:-1] for prefixe in CATEGORICAL_PREFIXES.values()]


def valeurs_connues_du_modele(colonnes_modele: list[str]) -> dict[str, set[str]]:
    """Pour chaque variable catégorielle, les valeurs que le modèle a vues à l'entraînement."""
    connues = {}
    for prefixe in CATEGORICAL_PREFIXES.values():
        connues[prefixe[:-1]] = {c[len(prefixe):] for c in colonnes_modele if c.startswith(prefixe)}
    return connues


def dedoublonner(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Une ligne par numero_dpe (la version modifiée le plus récemment)."""
    sans_id = df["numero_dpe"].isna()
    df = df[~sans_id]
    trie = df.sort_values(["date_derniere_modification_dpe", "date_etablissement_dpe"], na_position="first",
                          kind="mergesort")
    garde = trie.drop_duplicates("numero_dpe", keep="last").sort_index()
    return garde, {"sans_identifiant": int(sans_id.sum()), "doublons_identifiant": len(df) - len(garde)}


def retirer_remplaces(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Quand un DPE en remplace un autre et que les deux sont présents, ne garder que le plus récent.

    Le plus récent est celui dont date_etablissement_dpe est la plus tardive ; à date égale,
    on garde le DPE remplaçant. Les chaînes A→B→C se résolvent paire par paire (seul C reste).
    """
    dates = df.set_index("numero_dpe")["date_etablissement_dpe"]
    paires = df.loc[df["numero_dpe_remplace"].notna() & df["numero_dpe_remplace"].isin(dates.index),
                    ["numero_dpe", "numero_dpe_remplace", "date_etablissement_dpe"]]
    paires = paires[paires["numero_dpe"] != paires["numero_dpe_remplace"]]
    date_remplace = paires["numero_dpe_remplace"].map(dates)
    remplace_plus_recent = date_remplace > paires["date_etablissement_dpe"]
    perdants = set(paires.loc[~remplace_plus_recent, "numero_dpe_remplace"]) | set(
        paires.loc[remplace_plus_recent, "numero_dpe"])
    garde = df[~df["numero_dpe"].isin(perdants)]
    return garde, {
        "avec_numero_dpe_remplace": int(df["numero_dpe_remplace"].notna().sum()),
        "paires_presentes": len(paires),
        "remplace_plus_recent_que_remplacant": int(remplace_plus_recent.sum()),
        "lignes_retirees": len(df) - len(garde),
    }


def filtrer_etiquette(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    manquante = df["etiquette_dpe"].isna()
    invalide = ~manquante & ~df["etiquette_dpe"].isin(CLASSES_DPE)
    valeurs_invalides = df.loc[invalide, "etiquette_dpe"].value_counts().to_dict()
    return df[~(manquante | invalide)], {
        "manquante": int(manquante.sum()),
        "hors_A_G": int(invalide.sum()),
        "valeurs_hors_A_G": {str(k): int(v) for k, v in valeurs_invalides.items()},
    }


def filtrer_surface(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    s = df[SURFACE_COLUMN]
    absente = s.isna()
    trop_petite = ~absente & (s < SURFACE_MIN)
    trop_grande = ~absente & (s > SURFACE_MAX)
    return df[~(absente | trop_petite | trop_grande)], {
        "absente": int(absente.sum()),
        f"inferieure_a_{SURFACE_MIN}": int(trop_petite.sum()),
        f"superieure_a_{SURFACE_MAX}": int(trop_grande.sum()),
    }


def categories_inconnues(df: pd.DataFrame, connues: dict[str, set[str]]) -> dict[str, dict[str, int]]:
    """Valeurs absentes du modèle (y compris valeur manquante), comptées par variable. Rien n'est supprimé."""
    resultat = {}
    for variable, valeurs in connues.items():
        serie = df[variable].fillna("(manquant)")
        inconnues = serie[~serie.isin(valeurs)].value_counts()
        resultat[variable] = {str(k): int(v) for k, v in inconnues.items()}
    return resultat


def repartition(df: pd.DataFrame) -> dict[str, dict]:
    effectifs = df["etiquette_dpe"].value_counts().reindex(CLASSES_DPE, fill_value=0)
    total = int(effectifs.sum())
    return {c: {"effectif": int(n), "pourcentage": 100 * n / total if total else 0.0}
            for c, n in effectifs.items()}


def nettoyer(df: pd.DataFrame, colonnes_modele: list[str]) -> tuple[pd.DataFrame, dict]:
    etapes = []
    for nom, fonction in [
        ("Dédoublonnage par numero_dpe", dedoublonner),
        ("DPE remplacés (ne garder que le plus récent)", retirer_remplaces),
        ("Étiquette DPE manquante ou hors A–G", filtrer_etiquette),
        (f"Surface absente, < {SURFACE_MIN} m² ou > {SURFACE_MAX} m²", filtrer_surface),
    ]:
        avant = len(df)
        df, detail = fonction(df)
        etapes.append({"etape": nom, "avant": avant, "apres": len(df), "detail": detail})
    df = df.reset_index(drop=True)
    bilan = {
        "etapes": etapes,
        "categories_inconnues_du_modele": categories_inconnues(df, valeurs_connues_du_modele(colonnes_modele)),
        "repartition": repartition(df),
        "dates_etablissement": {"min": df["date_etablissement_dpe"].min(), "max": df["date_etablissement_dpe"].max()},
    }
    return df, bilan


def _n(x: int) -> str:
    return f"{x:,}".replace(",", " ")


def rapport(bilan: dict, extraction: dict, lignes_brutes: int) -> str:
    lignes_etapes = "\n".join(
        f"| {e['etape']} | {_n(e['avant'])} | {_n(e['apres'])} | {_n(e['avant'] - e['apres'])} | "
        f"{', '.join(f'{k} : {_n(v) if isinstance(v, int) else v}' for k, v in e['detail'].items())} |"
        for e in bilan["etapes"]
    )
    blocs_inconnues = []
    for variable, valeurs in bilan["categories_inconnues_du_modele"].items():
        if valeurs:
            liste = "\n".join(f"  - `{v}` : {_n(n)}" for v, n in valeurs.items())
            blocs_inconnues.append(f"- `{variable}` ({_n(sum(valeurs.values()))} lignes) :\n{liste}")
        else:
            blocs_inconnues.append(f"- `{variable}` : aucune valeur inconnue")
    total_inconnues = sum(sum(v.values()) for v in bilan["categories_inconnues_du_modele"].values())
    lignes_classes = "\n".join(
        f"| {c} | {_n(v['effectif'])} | {v['pourcentage']:.2f} % |" for c, v in bilan["repartition"].items()
    )
    final = bilan["etapes"][-1]["apres"]
    return f"""# Nettoyage des DPE PACA

Généré par `training/nettoyer.py`. Entrée : `data/dpe_r93_brut.parquet`
(extraction du {extraction['debut_extraction']}, {_n(extraction['lignes'])} lignes, SHA-256 `{extraction['sha256']}`).
Sortie : `data/dpe_paca.parquet`, **{_n(final)} lignes** ({100 * final / lignes_brutes:.2f} % du brut).

Périmètre de l'extraction : `{extraction['requete']['qs']}`.
Dates d'établissement après nettoyage : du {bilan['dates_etablissement']['min']} au {bilan['dates_etablissement']['max']}.

## Étapes

Appliquées dans cet ordre ; chaque ligne part du résultat de la précédente.

| Étape | Avant | Après | Retirées | Détail |
|---|---:|---:|---:|---|
{lignes_etapes}

Règles :
- dédoublonnage **par identifiant** (`numero_dpe`), jamais par contenu ; en cas de doublon, on garde la version
  dont `date_derniere_modification_dpe` est la plus récente ;
- DPE remplacés : `avec_numero_dpe_remplace` compte les DPE qui en remplacent un autre ; la plupart des DPE
  remplacés ne sont déjà plus dans le jeu ADEME, seules les `paires_presentes` sont traitées ici. Quand un DPE et celui qu'il remplace (`numero_dpe_remplace`) sont tous deux présents, on ne garde
  que celui dont `date_etablissement_dpe` est la plus récente (à date égale, le remplaçant) ;
- surface : bornes {SURFACE_MIN}–{SURFACE_MAX} m², identiques à la validation de `/predict`.

## Valeurs inconnues du modèle actuel

Comptées sur le jeu nettoyé, **non supprimées** ({_n(total_inconnues)} valeurs au total).
- Chauffage, période ou type de bâtiment inconnus : l'API refuse ces logements ; `training/evaluer.py` les exclut
  du test en les comptant.
- `zone_climatique` : sans effet sur l'évaluation, car l'API (comme `training/evaluer.py`) déduit la zone du
  département et n'utilise pas ce champ.

{chr(10).join(blocs_inconnues)}

## Répartition des classes DPE (PACA, jeu nettoyé)

| Classe | Effectif | Part |
|---|---:|---:|
{lignes_classes}
| **Total** | **{_n(final)}** | 100 % |
"""


def main() -> None:
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    brut = pd.read_parquet(ENTREE)
    df, bilan = nettoyer(brut, get_columns())
    df.to_parquet(SORTIE, index=False)
    RAPPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPPORT.write_bytes(rapport(bilan, extraction, len(brut)).encode("utf-8"))
    print(f"{len(brut)} → {len(df)} lignes ; rapport : {RAPPORT}")


if __name__ == "__main__":
    main()
