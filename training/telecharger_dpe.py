"""Téléchargement des DPE ADEME (jeu dpe03existant) via l'API data-fair.

Deux modes exclusifs :
  --region 93    télécharge toutes les maisons et appartements de la région
                 (pagination par le lien `next`, reprise possible après coupure) ;
  --metropole    ne télécharge rien : compte les lignes de la France métropolitaine,
                 estime taille et durée à partir de l'extraction régionale déjà faite,
                 et vérifie s'il existe un export complet (CSV/Parquet).

Usage (depuis la racine du dépôt) :
  .venv/Scripts/python.exe -m training.telecharger_dpe --region 93
  .venv/Scripts/python.exe -m training.telecharger_dpe --metropole
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DATA = RACINE / "data"
DOSSIER_REPORTS = RACINE / "reports"

DATASET_URL = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant"
DATAGOUV_URL = "https://www.data.gouv.fr/api/1/datasets/dpe-logements-existants-depuis-juillet-2021/"
TAILLE_PAGE = 10_000
LIMITE_REQUETES_PAR_MINUTE = 600  # limite anonyme annoncée par data.ademe.fr
PAUSE_ENTRE_PAGES = 0.5  # secondes : très en dessous de 600 requêtes/minute
FILTRE_TYPES = "type_batiment:(maison OR appartement)"

# Régions métropolitaines (codes INSEE), Corse comprise, DOM exclus
REGIONS_METROPOLE = {
    "11": "Île-de-France",
    "24": "Centre-Val de Loire",
    "27": "Bourgogne-Franche-Comté",
    "28": "Normandie",
    "32": "Hauts-de-France",
    "44": "Grand Est",
    "52": "Pays de la Loire",
    "53": "Bretagne",
    "75": "Nouvelle-Aquitaine",
    "76": "Occitanie",
    "84": "Auvergne-Rhône-Alpes",
    "93": "Provence-Alpes-Côte d'Azur",
    "94": "Corse",
}

CHAMPS_TEXTE = [
    "numero_dpe",
    "numero_dpe_remplace",
    "date_etablissement_dpe",
    "date_reception_dpe",
    "date_derniere_modification_dpe",
    "etiquette_dpe",
    "etiquette_ges",
    "periode_construction",
    "type_batiment",
    "type_energie_principale_chauffage",
    "zone_climatique",
    "code_postal_ban",
    "code_departement_ban",
    "code_region_ban",
    "type_energie_n1",
    "type_energie_n2",
    "type_energie_n3",
]
CHAMPS_NUMERIQUES = [
    "surface_habitable_logement",
    "conso_5_usages_par_m2_ep",
    "conso_5_usages_par_m2_ef",
    "conso_5_usages_ef",
    "emission_ges_5_usages_par_m2",
    "conso_5_usages_ef_energie_n1",
    "conso_5_usages_ef_energie_n2",
    "conso_5_usages_ef_energie_n3",
]
CHAMPS = CHAMPS_TEXTE + CHAMPS_NUMERIQUES

STATUTS_A_RETENTER = {429, 500, 502, 503, 504}


class ErreurTelechargement(RuntimeError):
    """Échec définitif après toutes les tentatives."""


# ── Utilitaires ──────────────────────────────────────────────────────────────

def ecrire_json(chemin: Path, donnees: dict) -> None:
    """Écrit un JSON en UTF-8 (sans BOM), de façon atomique."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(chemin.suffix + ".tmp")
    tmp.write_bytes(json.dumps(donnees, ensure_ascii=False, indent=2).encode("utf-8"))
    tmp.replace(chemin)


def ecrire_texte(chemin: Path, texte: str) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(texte.encode("utf-8"))


def sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_avec_reessais(session, url, params=None, max_tentatives=6, attente_base=2.0,
                      dormir=time.sleep, methode="GET"):
    """Requête HTTP avec nouvelles tentatives (erreurs réseau, 429, 5xx), délai croissant."""
    derniere_erreur = None
    for tentative in range(max_tentatives):
        try:
            if methode == "HEAD":
                reponse = session.head(url, params=params, timeout=120, allow_redirects=True)
            else:
                reponse = session.get(url, params=params, timeout=120)
        except requests.RequestException as e:
            derniere_erreur = f"erreur réseau : {e}"
        else:
            if reponse.status_code not in STATUTS_A_RETENTER:
                return reponse
            derniere_erreur = f"HTTP {reponse.status_code}"
            retry_after = reponse.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                dormir(float(retry_after))
                continue
        if tentative < max_tentatives - 1:
            dormir(attente_base * 2 ** tentative)
    raise ErreurTelechargement(f"{url} : échec après {max_tentatives} tentatives ({derniere_erreur})")


def filtre_region(code_region: str) -> str:
    return f"code_region_ban:{code_region} AND {FILTRE_TYPES}"


def params_initiaux(qs: str) -> dict:
    return {"size": TAILLE_PAGE, "qs": qs, "select": ",".join(CHAMPS)}


def page_vers_dataframe(resultats: list[dict]) -> pd.DataFrame:
    """Résultats d'une page → DataFrame aux colonnes et types fixes (schéma parquet stable)."""
    df = pd.DataFrame(resultats).reindex(columns=CHAMPS)
    for col in CHAMPS_TEXTE:
        df[col] = df[col].astype("string")
    for col in CHAMPS_NUMERIQUES:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    return df


# ── Mode --region : téléchargement paginé avec reprise ──────────────────────

def telecharger_pages(session, qs: str, dossier_pages: Path, pause: float = PAUSE_ENTRE_PAGES,
                      dormir=time.sleep, horloge=time.monotonic, journal=print) -> dict:
    """Télécharge toutes les pages dans `dossier_pages`, en reprenant là où on s'était arrêté.

    L'état (URL `next`, nombre de pages, lignes, octets, durée) est enregistré après
    chaque page dans `etat.json`. Une page est écrite avant la mise à jour de l'état :
    après une coupure, au pire la dernière page est retéléchargée et réécrite à l'identique.
    """
    dossier_pages.mkdir(parents=True, exist_ok=True)
    chemin_etat = dossier_pages / "etat.json"
    url_initiale = f"{DATASET_URL}/lines?{urlencode(params_initiaux(qs))}"

    if chemin_etat.exists():
        etat = json.loads(chemin_etat.read_text(encoding="utf-8"))
        if etat["url_initiale"] != url_initiale:
            raise ErreurTelechargement(
                f"{dossier_pages} contient une autre extraction ; supprimez-le pour recommencer.")
        if etat["termine"]:
            journal(f"Extraction déjà terminée : {etat['lignes']} lignes en {etat['pages']} pages.")
            return etat
        journal(f"Reprise après {etat['pages']} pages ({etat['lignes']} lignes).")
    else:
        etat = {
            "url_initiale": url_initiale,
            "debut": maintenant(),
            "prochaine_url": url_initiale,
            "pages": 0,
            "lignes": 0,
            "total_annonce": None,
            "octets_json": 0,
            "secondes_requetes": 0.0,
            "termine": False,
        }
        ecrire_json(chemin_etat, etat)

    while etat["prochaine_url"]:
        t0 = horloge()
        reponse = get_avec_reessais(session, etat["prochaine_url"], dormir=dormir)
        if reponse.status_code != 200:
            raise ErreurTelechargement(f"HTTP {reponse.status_code} : {reponse.text[:300]}")
        corps = reponse.json()
        duree = horloge() - t0
        resultats = corps.get("results", [])
        etat["total_annonce"] = corps.get("total", etat["total_annonce"])

        if resultats:
            numero = etat["pages"] + 1
            chemin_page = dossier_pages / f"page_{numero:05d}.parquet"
            tmp = chemin_page.with_suffix(".parquet.tmp")
            page_vers_dataframe(resultats).to_parquet(tmp, index=False)
            tmp.replace(chemin_page)
            etat["pages"] = numero
            etat["lignes"] += len(resultats)

        etat["octets_json"] += len(reponse.content)
        etat["secondes_requetes"] += duree
        etat["prochaine_url"] = corps.get("next") if resultats else None
        if not etat["prochaine_url"]:
            etat["termine"] = True
            etat["fin"] = maintenant()
        ecrire_json(chemin_etat, etat)
        journal(f"page {etat['pages']} : {etat['lignes']}/{etat['total_annonce']} lignes")
        if etat["prochaine_url"]:
            dormir(pause)
    return etat


def assembler_pages(dossier_pages: Path, sortie: Path) -> int:
    pages = sorted(dossier_pages.glob("page_*.parquet"))
    if not pages:
        raise ErreurTelechargement(f"Aucune page dans {dossier_pages}")
    df = pd.concat([pd.read_parquet(p) for p in pages], ignore_index=True)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(sortie, index=False)
    return len(df)


def mode_region(code_region: str, session) -> dict:
    qs = filtre_region(code_region)
    dossier_pages = DOSSIER_DATA / f"pages_r{code_region}"
    etat = telecharger_pages(session, qs, dossier_pages)
    sortie = DOSSIER_DATA / f"dpe_r{code_region}_brut.parquet"
    lignes = assembler_pages(dossier_pages, sortie)
    if lignes != etat["lignes"]:
        raise ErreurTelechargement(f"Incohérence : {lignes} lignes assemblées, {etat['lignes']} téléchargées")
    if etat["total_annonce"] is not None and lignes != etat["total_annonce"]:
        print(f"ATTENTION : {lignes} lignes reçues pour {etat['total_annonce']} annoncées par l'API")

    extraction = {
        "source": DATASET_URL,
        "region": code_region,
        "requete": {
            "url_initiale": etat["url_initiale"],
            "qs": qs,
            "select": CHAMPS,
            "taille_page": TAILLE_PAGE,
            "pagination": "lien next (curseur after)",
        },
        "debut_extraction": etat["debut"],
        "fin_extraction": etat.get("fin"),
        "lignes": lignes,
        "total_annonce_par_api": etat["total_annonce"],
        "pages": etat["pages"],
        "octets_json_recus": etat["octets_json"],
        "secondes_requetes": round(etat["secondes_requetes"], 1),
        "fichier": str(sortie.relative_to(RACINE)).replace("\\", "/"),
        "octets_parquet": sortie.stat().st_size,
        "sha256": sha256(sortie),
    }
    ecrire_json(DOSSIER_DATA / f"extraction_r{code_region}.json", extraction)
    ecrire_json(DOSSIER_REPORTS / f"extraction_r{code_region}.json", extraction)
    print(f"{lignes} lignes → {sortie} (sha256 {extraction['sha256'][:12]}…)")
    return extraction


# ── Mode --metropole : comptage, estimation, recherche d'un export complet ──

def compter(session, qs: str) -> int:
    reponse = get_avec_reessais(session, f"{DATASET_URL}/lines", params={"size": 0, "qs": qs})
    reponse.raise_for_status()
    return int(reponse.json()["total"])


def compter_par_region(session) -> dict[str, int]:
    reponse = get_avec_reessais(session, f"{DATASET_URL}/values_agg",
                                params={"field": "code_region_ban", "qs": FILTRE_TYPES, "agg_size": 50})
    reponse.raise_for_status()
    return {a["value"]: int(a["total"]) for a in reponse.json()["aggs"]}


def chercher_exports(session) -> dict:
    """Ce qui existe comme fichier complet, constaté au moment de l'exécution."""
    constats: dict = {}

    meta = get_avec_reessais(session, DATASET_URL).json()
    stockage = meta.get("storage") or {}
    constats["data_ademe"] = {
        "jeu_virtuel": bool(meta.get("isVirtual")),
        "fichier": meta.get("file"),
        "fichier_original": meta.get("originalFile"),
        "fichiers_de_donnees_stockes": stockage.get("dataFiles", []),
        "date_mise_a_jour_donnees": meta.get("dataUpdatedAt"),
    }
    full = get_avec_reessais(session, f"{DATASET_URL}/full", methode="HEAD")
    constats["data_ademe"]["statut_http_full"] = full.status_code
    data_files = get_avec_reessais(session, f"{DATASET_URL}/data-files")
    constats["data_ademe"]["data_files"] = data_files.json() if data_files.status_code == 200 else None

    dg = get_avec_reessais(session, DATAGOUV_URL)
    ressources = []
    if dg.status_code == 200:
        for r in dg.json().get("resources", []):
            ressources.append({"titre": r.get("title"), "format": r.get("format"),
                               "url": r.get("url"), "taille": r.get("filesize")})
    constats["data_gouv"] = {"statut_http": dg.status_code, "ressources": ressources}

    exports = []
    if constats["data_ademe"]["fichier"] or constats["data_ademe"]["fichiers_de_donnees_stockes"]:
        exports.append("fichier source data.ademe.fr")
    if full.status_code == 200:
        exports.append(f"{DATASET_URL}/full")
    for r in ressources:
        fmt = (r["format"] or "").lower()
        if fmt in {"csv", "parquet", "zip", "gz", "csv.gz"} and "data.ademe.fr/datasets/" not in (r["url"] or ""):
            exports.append(r["url"])
    constats["exports_complets_trouves"] = exports
    return constats


def estimer(lignes: int, extraction: dict) -> dict:
    """Estimation de taille et de durée à partir des mesures de l'extraction régionale."""
    ref = extraction["lignes"]
    pages = math.ceil(lignes / TAILLE_PAGE)
    sec_par_page = extraction["secondes_requetes"] / extraction["pages"]
    duree_mesuree = pages * (sec_par_page + PAUSE_ENTRE_PAGES)
    return {
        "lignes": lignes,
        "pages_de_10000": pages,
        "octets_json_par_ligne_mesures": extraction["octets_json_recus"] / ref,
        "octets_parquet_par_ligne_mesures": extraction["octets_parquet"] / ref,
        "taille_json_estimee_octets": round(lignes * extraction["octets_json_recus"] / ref),
        "taille_parquet_estimee_octets": round(lignes * extraction["octets_parquet"] / ref),
        "secondes_par_page_mesurees": sec_par_page,
        "duree_estimee_secondes": round(duree_mesuree),
        "duree_plancher_limite_debit_secondes": round(pages * 60 / LIMITE_REQUETES_PAR_MINUTE),
    }


def _n(x: int) -> str:
    return f"{x:,}".replace(",", " ")


def _go(octets: float) -> str:
    return f"{octets / 1e9:.2f} Go"


def _duree(sec: float) -> str:
    h, reste = divmod(int(sec), 3600)
    return f"{h} h {reste // 60:02d} min"


def rapport_metropole(res: dict) -> str:
    e = res["estimation"]
    ex = res["exports"]
    lignes_regions = "\n".join(
        f"| {code} | {nom} | {_n(res['par_region'].get(code, 0))} |"
        for code, nom in REGIONS_METROPOLE.items()
    )
    ressources = "\n".join(
        f"- {r['titre']} — format `{r['format']}` — {r['url']}" for r in ex["data_gouv"]["ressources"]
    ) or "- (aucune)"
    trouves = "\n".join(f"- {u}" for u in ex["exports_complets_trouves"]) or "- aucun"
    return f"""# Estimation d'une extraction France métropolitaine (sans téléchargement)

Généré par `training/telecharger_dpe.py --metropole` le {res['date']}.
Source : `{DATASET_URL}` (données mises à jour le {ex['data_ademe']['date_mise_a_jour_donnees']}).
Périmètre : maisons et appartements des 13 régions métropolitaines (Corse comprise, DOM exclus).

## Volume

- Requête de comptage : `{res['qs']}`
- **{_n(res['total'])} lignes** (somme par région : {_n(res['somme_par_region'])} ; écart : {_n(res['total'] - res['somme_par_region'])})

| Code | Région | DPE maisons + appartements |
|---|---|---:|
{lignes_regions}

## Taille et durée estimées par l'API

Mesures de référence : extraction de la région {res['reference']['region']} ({_n(res['reference']['lignes'])} lignes, {res['reference']['pages']} pages).

| | Valeur |
|---|---:|
| Pages de {_n(TAILLE_PAGE)} lignes | {_n(e['pages_de_10000'])} |
| Octets JSON reçus par ligne (mesurés) | {e['octets_json_par_ligne_mesures']:.0f} |
| Octets Parquet par ligne (mesurés) | {e['octets_parquet_par_ligne_mesures']:.0f} |
| Volume JSON à transférer | {_go(e['taille_json_estimee_octets'])} |
| Fichier Parquet final | {_go(e['taille_parquet_estimee_octets'])} |
| Secondes par page (mesurées) | {e['secondes_par_page_mesurees']:.2f} |
| Durée estimée (débit mesuré + pause de {PAUSE_ENTRE_PAGES} s) | {_duree(e['duree_estimee_secondes'])} |
| Durée minimale imposée par la limite de {LIMITE_REQUETES_PAR_MINUTE} req/min | {_duree(e['duree_plancher_limite_debit_secondes'])} |

## Export complet disponible ?

data.ademe.fr :
- jeu virtuel : {ex['data_ademe']['jeu_virtuel']}
- fichier source : {ex['data_ademe']['fichier']} ; fichier original : {ex['data_ademe']['fichier_original']} ; fichiers de données stockés : {ex['data_ademe']['fichiers_de_donnees_stockes']}
- `GET /full` : HTTP {ex['data_ademe']['statut_http_full']}
- `GET /data-files` : {ex['data_ademe']['data_files']}

data.gouv.fr (fiche « DPE Logements existants (depuis juillet 2021) », HTTP {ex['data_gouv']['statut_http']}) :
{ressources}

Exports complets (CSV/Parquet) trouvés :
{trouves}

## Conclusion

{res['conclusion']}
"""


def conclure(exports: dict, estimation: dict) -> str:
    pages = f"{estimation['pages_de_10000']:,}".replace(",", " ")
    if exports["exports_complets_trouves"]:
        return ("Un export complet est disponible : il est plus adapté que l'API pour la métropole "
                f"(un seul téléchargement au lieu de {pages} requêtes paginées).")
    return ("Aucun export complet (CSV ou Parquet) n'a été trouvé sur data.ademe.fr ni sur data.gouv.fr : "
            "le jeu est servi uniquement par l'API. L'extraction métropole par l'API reste faisable avec le "
            f"même script ({pages} pages, durée estimée {_duree(estimation['duree_estimee_secondes'])}, "
            "reprise possible), de préférence région par région pour limiter la perte en cas de coupure.")


def mode_metropole(session, code_reference: str = "93") -> dict:
    chemin_ref = DOSSIER_DATA / f"extraction_r{code_reference}.json"
    if not chemin_ref.exists():
        sys.exit(f"{chemin_ref} introuvable : lancez d'abord --region {code_reference} "
                 "(les estimations reposent sur ses mesures).")
    extraction = json.loads(chemin_ref.read_text(encoding="utf-8"))

    codes = " OR ".join(REGIONS_METROPOLE)
    qs = f"code_region_ban:({codes}) AND {FILTRE_TYPES}"
    total = compter(session, qs)
    par_region = {c: n for c, n in compter_par_region(session).items() if c in REGIONS_METROPOLE}
    estimation = estimer(total, extraction)
    exports = chercher_exports(session)

    res = {
        "date": maintenant(),
        "qs": qs,
        "total": total,
        "par_region": par_region,
        "somme_par_region": sum(par_region.values()),
        "reference": {k: extraction[k] for k in ("region", "lignes", "pages", "octets_json_recus",
                                                 "octets_parquet", "secondes_requetes")},
        "estimation": estimation,
        "exports": exports,
    }
    res["conclusion"] = conclure(exports, estimation)
    ecrire_json(DOSSIER_REPORTS / "estimation_metropole.json", res)
    ecrire_texte(DOSSIER_REPORTS / "estimation_metropole.md", rapport_metropole(res))
    print(res["conclusion"])
    return res


def nouvelle_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = "energyhome-api/telecharger_dpe"
    return session


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    groupe = parser.add_mutually_exclusive_group(required=True)
    groupe.add_argument("--region", help="code INSEE de la région à télécharger (ex. 93 pour PACA)")
    groupe.add_argument("--metropole", action="store_true",
                        help="compter et estimer la France métropolitaine, sans rien télécharger")
    args = parser.parse_args(argv)
    session = nouvelle_session()
    if args.metropole:
        mode_metropole(session)
    else:
        if not args.region.isdigit():
            parser.error("--region attend un code INSEE numérique (ex. 93)")
        mode_region(args.region, session)


if __name__ == "__main__":
    main()
