"""Validation du recalcul d'étiquette avant tout entraînement.

On recalcule l'étiquette de chaque DPE à son propre coefficient (1,9 depuis le
2026-01-01, contrôle à 2,3 avant) avec les règles de l'arrêté du 25 mars 2024
(app/core/reglementation.py), et on la compare à `etiquette_dpe`. On mesure aussi
l'effet des seuils petites surfaces (avant/après le 1er juillet 2024) et de l'altitude.

Entrées : data/dpe_paca.parquet, data/altitude_r93.parquet (training/telecharger_altitude.py)
Sorties : reports/validation_etiquettes.json et reports/validation_etiquettes.md

Usage : .venv/Scripts/python.exe -m training.valider_etiquettes
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.reglementation import DATE_SEUILS_PETITES_SURFACES, SOURCE_SEUILS, ZONES_ALTITUDE
from training.etiquettes import ALTITUDE_SUP_800, CLASSES, indices_lot, recalculer_lot

RACINE = Path(__file__).resolve().parent.parent
ENTREE = RACINE / "data" / "dpe_paca.parquet"
ALTITUDE = RACINE / "data" / "altitude_r93.parquet"
SORTIE_JSON = RACINE / "reports" / "validation_etiquettes.json"
SORTIE_MD = RACINE / "reports" / "validation_etiquettes.md"

DATE_19 = pd.Timestamp("2026-01-01")
DATE_PS = pd.Timestamp(DATE_SEUILS_PETITES_SURFACES)
TRANCHES = [("< 40 m²", 0, 40), ("40–100 m²", 40, 100), ("> 100 m²", 100, np.inf)]
BORNES_FINES = [0, 10, 15, 20, 25, 30, 35, 40, 40.0001, 45, 50, np.inf]
DEPARTEMENTS_ALTITUDE = ["04", "05", "84"]
N_EXEMPLES = 15


def charger() -> tuple[pd.DataFrame, dict]:
    df = pd.read_parquet(ENTREE)
    alt = pd.read_parquet(ALTITUDE)
    n = len(df)
    df = df.merge(alt, on="numero_dpe", how="left", validate="one_to_one")
    assert len(df) == n
    jointure = {
        "dpe": n,
        "avec_classe_altitude": int(df["classe_altitude"].notna().sum()),
        "sans_classe_altitude": int(df["classe_altitude"].isna().sum()),
        "repartition": {str(k): int(v) for k, v in df["classe_altitude"].value_counts(dropna=False).items()},
    }
    return df, jointure


def _taux(ok: pd.Series, masque=None) -> dict:
    s = ok if masque is None else ok[masque]
    return {"n": int(s.size), "concordance": float(s.mean()) if s.size else None}


def comparer(df: pd.DataFrame, coefficient: float) -> dict:
    """Concordance avec les règles complètes, et détail des écarts."""
    recalc = recalculer_lot(df, coefficient)
    vrai = df["etiquette_dpe"].astype(str)
    ok = recalc == vrai
    surface = df["surface_habitable_logement"]
    ecart = vrai.map(CLASSES.index) - recalc.map(CLASSES.index)

    par_tranche = {nom: _taux(ok, (surface >= bas) & (surface < haut)) for nom, bas, haut in TRANCHES}
    fine = pd.cut(surface, BORNES_FINES, right=False)
    par_surface_fine = {str(k): _taux(g) for k, g in ok.groupby(fine, observed=True)}
    par_chauffage = {str(k): _taux(g) for k, g in ok.groupby(df["type_energie_principale_chauffage"].astype(str))}
    confusion = pd.crosstab(vrai, recalc).reindex(index=CLASSES, columns=CLASSES, fill_value=0)

    cols = ["numero_dpe", "date_etablissement_dpe", "surface_habitable_logement", "type_energie_principale_chauffage",
            "zone_climatique", "classe_altitude", "conso_5_usages_par_m2_ep", "emission_ges_5_usages_par_m2", "etiquette_dpe"]
    ex = df.loc[~ok, cols].copy()
    ex["etiquette_recalculee"] = recalc[~ok]
    ex = ex.sample(min(N_EXEMPLES, len(ex)), random_state=42) if len(ex) else ex
    ex["date_etablissement_dpe"] = ex["date_etablissement_dpe"].astype(str)

    return {
        "coefficient": coefficient,
        **_taux(ok),
        "par_tranche": par_tranche,
        "par_surface_fine": par_surface_fine,
        "desaccords": {"total": int((~ok).sum()), "officiel_meilleur": int((ecart < 0).sum()),
                       "officiel_plus_mauvais": int((ecart > 0).sum())},
        "par_chauffage": par_chauffage,
        "confusion_reel_lignes_recalcule_colonnes": confusion.values.tolist(),
        "exemples_ecarts": ex.astype(object).where(ex.notna(), None).to_dict(orient="records"),
    }


def petites_surfaces_avant_apres(df: pd.DataFrame) -> dict:
    """Concordance ≤ 40 m², avec et sans les seuils petites surfaces, avant et après le 2024-07-01."""
    petit = df["surface_habitable_logement"] <= 40
    d = pd.to_datetime(df["date_etablissement_dpe"])
    sous = df[petit & (d < DATE_19)]  # coefficient 2,3 sur toute la période comparée
    ds = pd.to_datetime(sous["date_etablissement_dpe"])
    vrai = sous["etiquette_dpe"].astype(str)
    res = {}
    for nom, ps in (("seuils_petites_surfaces", True), ("seuils_standards", False)):
        ok = recalculer_lot(sous, 2.3, petites_surfaces=ps) == vrai
        res[nom] = {"avant_2024_07_01": _taux(ok, ds < DATE_PS), "depuis_2024_07_01": _taux(ok, ds >= DATE_PS)}
    # Même mesure sur les DPE 2026 (coefficient 1,9), tous postérieurs au 2024-07-01
    s26 = df[petit & (d >= DATE_19)]
    v26 = s26["etiquette_dpe"].astype(str)
    res["depuis_2026_coef_1_9"] = {
        "seuils_petites_surfaces": _taux(recalculer_lot(s26, 1.9, True) == v26),
        "seuils_standards": _taux(recalculer_lot(s26, 1.9, False) == v26),
    }
    trimestre = ds.dt.to_period("Q").astype(str)
    ok_ps = recalculer_lot(sous, 2.3, True) == vrai
    ok_std = recalculer_lot(sous, 2.3, False) == vrai
    res["par_trimestre"] = {t: {"seuils_petites_surfaces": float(ok_ps[trimestre == t].mean()),
                                "seuils_standards": float(ok_std[trimestre == t].mean()),
                                "n": int((trimestre == t).sum())}
                            for t in sorted(trimestre.unique())}
    return res


def effet_altitude(df: pd.DataFrame, coefficient: float) -> dict:
    """Concordance avec et sans la règle d'altitude, par département."""
    vrai = df["etiquette_dpe"].astype(str)
    ok_avec = recalculer_lot(df, coefficient) == vrai
    ok_sans = recalculer_lot(df.drop(columns="classe_altitude"), coefficient) == vrai
    concernes = ((df["classe_altitude"] == ALTITUDE_SUP_800) & df["zone_climatique"].isin(ZONES_ALTITUDE))
    dep = df["code_departement_ban"].astype(str)
    par_dep = {}
    for code in sorted(dep.unique()):
        m = dep == code
        par_dep[code] = {
            "n": int(m.sum()),
            "concernes_altitude": int((m & concernes).sum()),
            "concordance_sans_altitude": float(ok_sans[m].mean()),
            "concordance_avec_altitude": float(ok_avec[m].mean()),
            "concordance_concernes_sans": float(ok_sans[m & concernes].mean()) if (m & concernes).any() else None,
            "concordance_concernes_avec": float(ok_avec[m & concernes].mean()) if (m & concernes).any() else None,
        }
    plus_800_hors_zones = (df["classe_altitude"] == ALTITUDE_SUP_800) & ~df["zone_climatique"].isin(ZONES_ALTITUDE)
    return {
        "coefficient": coefficient,
        "concordance_sans_altitude": float(ok_sans.mean()),
        "concordance_avec_altitude": float(ok_avec.mean()),
        "concernes": int(concernes.sum()),
        "plus_de_800m_hors_zones_H1b_H1c_H2d": int(plus_800_hors_zones.sum()),
        "par_departement": par_dep,
    }


def effet_cible(df: pd.DataFrame) -> dict:
    """Combien d'étiquettes la cible en 1,9 change, avant 2026 (par chauffage électrique ou non)."""
    avant = df[pd.to_datetime(df["date_etablissement_dpe"]) < DATE_19]
    # Hypothèse de la table datée (source = coefficient à la date du DPE), conservée pour mémoire
    vrai = avant["etiquette_dpe"].astype(str)
    indice = np.clip(vrai.map(CLASSES.index).to_numpy() + indices_lot(avant, 1.9) - indices_lot(avant, 2.3), 0, 6)
    cible = pd.Series(np.asarray(CLASSES)[indice], index=avant.index)
    decalage = cible.map(CLASSES.index) - vrai.map(CLASSES.index)
    elec = avant["type_energie_principale_chauffage"].astype(str).str.startswith("Électricité")
    return {
        "dpe": int(len(avant)),
        "decalages": {str(int(k)): int(v) for k, v in decalage.value_counts().sort_index().items()},
        "part_changee_electrique": float((decalage[elec] != 0).mean()),
        "part_changee_autres": float((decalage[~elec] != 0).mean()),
        "repartition_officielle": {c: int((vrai == c).sum()) for c in CLASSES},
        "repartition_cible": {c: int((cible == c).sum()) for c in CLASSES},
        "electrique": _repartitions_comparees(df, avant, vrai, cible, elec, True),
        "autres": _repartitions_comparees(df, avant, vrai, cible, elec, False),
    }


def _repartitions_comparees(df, avant, vrai, cible, elec, electrique: bool) -> dict:
    """Parts par classe : officielle avant 2026, cible 1,9 avant 2026, officielle depuis 2026 (réellement en 1,9)."""
    d26 = df[pd.to_datetime(df["date_etablissement_dpe"]) >= DATE_19]
    e26 = d26["type_energie_principale_chauffage"].astype(str).str.startswith("Électricité")
    m = elec if electrique else ~elec
    v26 = d26.loc[e26 if electrique else ~e26, "etiquette_dpe"].astype(str)
    part = lambda s: {c: float((s == c).mean()) for c in CLASSES}
    return {"avant_2026_officielle": part(vrai[m]), "avant_2026_cible_1_9": part(cible[m]),
            "depuis_2026_officielle": part(v26), "n_avant": int(m.sum()), "n_depuis": int(len(v26))}


def coefficient_observe(df: pd.DataFrame) -> dict:
    """Coefficient électricité réellement contenu dans les données publiées.

    Pour les DPE dont la seule énergie est l'électricité, CEP / CEF par m² vaut le
    coefficient appliqué (aux arrondis près). Mesuré par trimestre d'établissement.
    """
    seul_elec = (df["type_energie_n1"].astype("string").str.startswith("Électricité").fillna(False)
                 & df["type_energie_n2"].isna() & df["type_energie_n3"].isna())
    sous = df[seul_elec]
    ratio = sous["conso_5_usages_par_m2_ep"] / sous["conso_5_usages_par_m2_ef"]
    d = pd.to_datetime(sous["date_etablissement_dpe"])
    trimestre = d.dt.to_period("Q").astype(str)

    def stats(r: pd.Series) -> dict:
        return {"n": int(r.size), "p10": float(r.quantile(0.1)), "mediane": float(r.median()),
                "p90": float(r.quantile(0.9)),
                "part_entre_1_85_et_1_95": float(r.between(1.85, 1.95).mean()),
                "part_entre_2_25_et_2_35": float(r.between(2.25, 2.35).mean())}

    return {
        "avant_2026": stats(ratio[d < DATE_19]),
        "depuis_2026": stats(ratio[d >= DATE_19]),
        "par_trimestre": {t: stats(g) for t, g in ratio.groupby(trimestre)},
    }


def section_coefficient(r: dict) -> str:
    l = ["## Coefficient électricité réellement présent dans les données", "",
         "DPE dont la seule énergie est l'électricité : rapport CEP / CEF par m² (égal au coefficient appliqué, "
         "aux arrondis près).", "",
         "| Période | DPE | 10e centile | Médiane | 90e centile | Part entre 1,85 et 1,95 | Part entre 2,25 et 2,35 |",
         "|---|---:|---:|---:|---:|---:|---:|"]
    lignes = [("Avant 2026", r["avant_2026"]), ("Depuis 2026", r["depuis_2026"])] + list(r["par_trimestre"].items())
    for nom, v in lignes:
        l.append(f"| {nom} | {_n(v['n'])} | {v['p10']:.3f} | {v['mediane']:.3f} | {v['p90']:.3f} | "
                 f"{_p(v['part_entre_1_85_et_1_95'])} | {_p(v['part_entre_2_25_et_2_35'])} |")
    return "\n".join(l)


# ── Rapport ─────────────────────────────────────────────────────────────────

def _n(x) -> str:
    return f"{x:,}".replace(",", " ")


def _p(x) -> str:
    return "—" if x is None else f"{100 * x:.2f} %"


def section(titre: str, r: dict) -> str:
    l = [f"## {titre}", "",
         f"- DPE comparés : {_n(r['n'])}, coefficient {r['coefficient']}",
         f"- **Concordance globale : {_p(r['concordance'])}**",
         f"- Désaccords : {_n(r['desaccords']['total'])} (étiquette officielle meilleure : "
         f"{_n(r['desaccords']['officiel_meilleur'])}, plus mauvaise : {_n(r['desaccords']['officiel_plus_mauvais'])})",
         "", "| Tranche de surface | DPE | Concordance |", "|---|---:|---:|"]
    l += [f"| {k} | {_n(v['n'])} | {_p(v['concordance'])} |" for k, v in r["par_tranche"].items()]
    l += ["", "| Surface (m²) | DPE | Concordance |", "|---|---:|---:|"]
    l += [f"| {k} | {_n(v['n'])} | {_p(v['concordance'])} |" for k, v in r["par_surface_fine"].items()]
    l += ["", "| Chauffage principal | DPE | Concordance |", "|---|---:|---:|"]
    l += [f"| {k} | {_n(v['n'])} | {_p(v['concordance'])} |"
          for k, v in sorted(r["par_chauffage"].items(), key=lambda kv: -kv[1]["n"])]
    l += ["", "Matrice réel (lignes) / recalculé (colonnes) :", "",
          "| | " + " | ".join(CLASSES) + " |", "|---|" + "---:|" * len(CLASSES)]
    l += [f"| **{c}** | " + " | ".join(_n(x) for x in ligne) + " |"
          for c, ligne in zip(CLASSES, r["confusion_reel_lignes_recalcule_colonnes"])]
    if r["exemples_ecarts"]:
        l += ["", "Exemples d'écarts (tirés au hasard, graine 42) :", "",
              "| N° DPE | Date | Surface | Chauffage | Zone | Altitude | CEP | EGES | Réel | Recalculé |",
              "|---|---|---:|---|---|---|---:|---:|---|---|"]
        for e in r["exemples_ecarts"]:
            l.append(f"| {e['numero_dpe']} | {e['date_etablissement_dpe'][:10]} | {e['surface_habitable_logement']:.1f} | "
                     f"{e['type_energie_principale_chauffage']} | {e['zone_climatique']} | {e['classe_altitude']} | "
                     f"{e['conso_5_usages_par_m2_ep']:.1f} | {e['emission_ges_5_usages_par_m2']:.1f} | "
                     f"{e['etiquette_dpe']} | {e['etiquette_recalculee']} |")
    return "\n".join(l)


def section_petites(r: dict) -> str:
    l = ["## Petites surfaces (≤ 40 m²) avant et après le 1er juillet 2024", "",
         "DPE établis avant 2026 (coefficient 2,3), recalculés avec ou sans les seuils petites surfaces :", "",
         "| Seuils appliqués | Avant le 2024-07-01 | Depuis le 2024-07-01 |", "|---|---:|---:|"]
    for nom, libelle in (("seuils_petites_surfaces", "Petites surfaces (arrêté 2024)"), ("seuils_standards", "Standards")):
        a, d = r[nom]["avant_2024_07_01"], r[nom]["depuis_2024_07_01"]
        l.append(f"| {libelle} | {_p(a['concordance'])} ({_n(a['n'])} DPE) | {_p(d['concordance'])} ({_n(d['n'])} DPE) |")
    r26 = r["depuis_2026_coef_1_9"]
    l += ["", f"DPE ≤ 40 m² établis depuis le 2026-01-01 (coefficient 1,9) : "
              f"{_p(r26['seuils_petites_surfaces']['concordance'])} avec les seuils petites surfaces, "
              f"{_p(r26['seuils_standards']['concordance'])} avec les seuils standards "
              f"({_n(r26['seuils_standards']['n'])} DPE).",
          "", "| Trimestre | DPE ≤ 40 m² | Seuils petites surfaces | Seuils standards |", "|---|---:|---:|---:|"]
    l += [f"| {t} | {_n(v['n'])} | {_p(v['seuils_petites_surfaces'])} | {_p(v['seuils_standards'])} |"
          for t, v in r["par_trimestre"].items()]
    return "\n".join(l)


def section_altitude(r: dict, jointure: dict) -> str:
    l = ["## Effet de la règle d'altitude (> 800 m en H1b, H1c, H2d)", "",
         f"Jointure de `classe_altitude` par `numero_dpe` : {_n(jointure['avec_classe_altitude'])} DPE renseignés, "
         f"{_n(jointure['sans_classe_altitude'])} sans valeur. Répartition : "
         + ", ".join(f"{k} : {_n(v)}" for k, v in jointure["repartition"].items()) + ".", "",
         f"DPE établis depuis le 2026-01-01 (coefficient {r['coefficient']}) : concordance "
         f"{_p(r['concordance_sans_altitude'])} sans la règle, {_p(r['concordance_avec_altitude'])} avec. "
         f"DPE concernés par la règle : {_n(r['concernes'])} ; à plus de 800 m mais hors zones H1b/H1c/H2d : "
         f"{_n(r['plus_de_800m_hors_zones_H1b_H1c_H2d'])}.", "",
         "| Département | DPE | Concernés | Concordance sans | Concordance avec | Concernés : sans | Concernés : avec |",
         "|---|---:|---:|---:|---:|---:|---:|"]
    for code, v in r["par_departement"].items():
        gras = "**" if code in DEPARTEMENTS_ALTITUDE else ""
        l.append(f"| {gras}{code}{gras} | {_n(v['n'])} | {_n(v['concernes_altitude'])} | {_p(v['concordance_sans_altitude'])} | "
                 f"{_p(v['concordance_avec_altitude'])} | {_p(v['concordance_concernes_sans'])} | {_p(v['concordance_concernes_avec'])} |")
    return "\n".join(l)


def section_cible(r: dict) -> str:
    l = ["## Effet de la cible d'entraînement (DPE d'avant 2026 ramenés en 1,9)", "",
         "**Attention** : ce calcul suppose, comme la table datée, que les DPE d'avant 2026 sont publiés en 2,3. "
         "La section précédente montre qu'ils sont publiés en 1,9 : ce décalage serait alors une double correction.", "",
         "Cible = `etiquette_dpe` décalée de (classe recalculée en 1,9 − classe recalculée en 2,3), mêmes seuils.", "",
         f"- DPE : {_n(r['dpe'])} ; décalages : " + ", ".join(f"{k} : {_n(v)}" for k, v in r["decalages"].items()),
         f"- Étiquettes changées : {_p(r['part_changee_electrique'])} des chauffages électriques, "
         f"{_p(r['part_changee_autres'])} des autres", "",
         "| Classe | Officielle | Cible 1,9 |", "|---|---:|---:|"]
    l += [f"| {c} | {_n(r['repartition_officielle'][c])} | {_n(r['repartition_cible'][c])} |" for c in CLASSES]
    for cle, titre in (("electrique", "Chauffage électrique"), ("autres", "Autres chauffages")):
        g = r[cle]
        l += ["", f"{titre} — parts par classe ({_n(g['n_avant'])} DPE avant 2026, {_n(g['n_depuis'])} depuis) :", "",
              "| Classe | Avant 2026, officielle (2,3) | Avant 2026, cible 1,9 | Depuis 2026, officielle (1,9) |",
              "|---|---:|---:|---:|"]
        l += [f"| {c} | {_p(g['avant_2026_officielle'][c])} | {_p(g['avant_2026_cible_1_9'][c])} | "
              f"{_p(g['depuis_2026_officielle'][c])} |" for c in CLASSES]
    return "\n".join(l)


def main() -> None:
    df, jointure = charger()
    d = pd.to_datetime(df["date_etablissement_dpe"])
    depuis_2026, avant_2026 = df[d >= DATE_19], df[d < DATE_19]
    res = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_seuils": SOURCE_SEUILS,
        "jointure_altitude": jointure,
        "depuis_2026_coef_1_9": comparer(depuis_2026, 1.9),
        "avant_2026_coef_2_3": comparer(avant_2026, 2.3),
        "petites_surfaces": petites_surfaces_avant_apres(df),
        "altitude": effet_altitude(depuis_2026, 1.9),
        "cible": effet_cible(df),
        "coefficient_observe": coefficient_observe(df),
    }
    SORTIE_JSON.write_bytes(json.dumps(res, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    md = "\n\n".join([
        "# Validation du recalcul des étiquettes",
        f"Généré par `training/valider_etiquettes.py` le {res['genere_le']}.\n\n"
        f"Règles appliquées ({SOURCE_SEUILS}) : CEP et EGES arrondis à l'entier inférieur, inégalités strictes, "
        "seuils petites surfaces (≤ 40 m², interpolation linéaire) et altitude (> 800 m en H1b, H1c, H2d). "
        "La surface utilisée est `surface_habitable_logement` : le jeu ADEME ne publie pas la surface de référence.\n\n"
        "Recalculer un DPE à son propre coefficient n'applique aucune correction : les deux premières sections "
        "valident les seuils, pas le coefficient. Le coefficient réellement présent dans les données est mesuré plus bas.",
        section("DPE établis depuis le 2026-01-01, coefficient 1,9 (aucune correction : seuils seuls)", res["depuis_2026_coef_1_9"]),
        section("DPE établis avant 2026, coefficient lu dans la table datée : 2,3 (aucune correction : seuils seuls)", res["avant_2026_coef_2_3"]),
        section_petites(res["petites_surfaces"]),
        section_altitude(res["altitude"], jointure),
        section_coefficient(res["coefficient_observe"]),
        section_cible(res["cible"]),
    ]) + "\n"
    SORTIE_MD.write_bytes(md.encode("utf-8"))
    for cle in ("depuis_2026_coef_1_9", "avant_2026_coef_2_3"):
        r = res[cle]
        print(cle, _p(r["concordance"]), {k: _p(v["concordance"]) for k, v in r["par_tranche"].items()})


if __name__ == "__main__":
    main()
