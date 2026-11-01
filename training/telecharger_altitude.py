"""Téléchargement de la classe d'altitude des DPE PACA, à joindre par `numero_dpe`.

Le champ `classe_altitude` manquait à l'extraction de l'étape 2. Plutôt que de tout
retélécharger (ce qui changerait le jeu, donc le test temporel), on ne récupère que
les deux colonnes `numero_dpe` et `classe_altitude`, avec le même filtre, et on les
joint au jeu nettoyé existant sans en modifier aucune ligne.

Sorties : data/altitude_r93.parquet, data/altitude_r93.json et reports/altitude_r93.json

Usage : .venv/Scripts/python.exe -m training.telecharger_altitude
"""

from __future__ import annotations

import time
from urllib.parse import urlencode

import pandas as pd
import requests

from training.telecharger_dpe import (
    DATASET_URL,
    DOSSIER_DATA,
    DOSSIER_REPORTS,
    PAUSE_ENTRE_PAGES,
    RACINE,
    TAILLE_PAGE,
    ErreurTelechargement,
    ecrire_json,
    filtre_region,
    get_avec_reessais,
    maintenant,
    sha256,
)

CHAMPS_ALTITUDE = ["numero_dpe", "classe_altitude"]
SORTIE = DOSSIER_DATA / "altitude_r93.parquet"


def telecharger(session, code_region: str = "93", pause: float = PAUSE_ENTRE_PAGES, journal=print) -> tuple[pd.DataFrame, dict]:
    qs = filtre_region(code_region)
    url = f"{DATASET_URL}/lines?{urlencode({'size': TAILLE_PAGE, 'qs': qs, 'select': ','.join(CHAMPS_ALTITUDE)})}"
    url_initiale, debut, pages, morceaux, total = url, maintenant(), 0, [], None
    while url:
        reponse = get_avec_reessais(session, url)
        if reponse.status_code != 200:
            raise ErreurTelechargement(f"HTTP {reponse.status_code} : {reponse.text[:300]}")
        corps = reponse.json()
        total = corps.get("total", total)
        resultats = corps.get("results", [])
        if resultats:
            morceaux.append(pd.DataFrame(resultats).reindex(columns=CHAMPS_ALTITUDE).astype("string"))
            pages += 1
        url = corps.get("next") if resultats else None
        journal(f"page {pages} : {sum(len(m) for m in morceaux)}/{total}")
        if url:
            time.sleep(pause)
    df = pd.concat(morceaux, ignore_index=True)
    return df, {"url_initiale": url_initiale, "qs": qs, "debut": debut, "fin": maintenant(),
                "pages": pages, "total_annonce_par_api": total}


def main() -> None:
    with requests.Session() as session:
        df, meta = telecharger(session)
    doublons = int(df["numero_dpe"].duplicated().sum())
    df = df.drop_duplicates("numero_dpe")
    df.to_parquet(SORTIE, index=False)
    bilan = {
        "source": DATASET_URL,
        **meta,
        "lignes": int(len(df)),
        "doublons_numero_dpe_retires": doublons,
        "repartition_classe_altitude": {str(k): int(v) for k, v in df["classe_altitude"].value_counts(dropna=False).items()},
        "fichier": str(SORTIE.relative_to(RACINE)).replace("\\", "/"),
        "sha256": sha256(SORTIE),
    }
    ecrire_json(DOSSIER_DATA / "altitude_r93.json", bilan)
    ecrire_json(DOSSIER_REPORTS / "altitude_r93.json", bilan)
    print(f"{len(df)} lignes → {SORTIE}")


if __name__ == "__main__":
    main()
