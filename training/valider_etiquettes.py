"""Validation du recalcul d'étiquette avant tout entraînement.

On recalcule l'étiquette de chaque DPE à son propre coefficient (1,9 depuis le
2026-01-01, contrôle à 2,3 avant) et on la compare à `etiquette_dpe`. Si le
recalcul est juste, la concordance doit être proche de 100 %.

Entrée  : data/dpe_paca.parquet
Sorties : reports/validation_etiquettes.json et reports/validation_etiquettes.md

Usage : .venv/Scripts/python.exe -m training.valider_etiquettes
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from training.etiquettes import (
    CLASSES,
    SEUILS_ENERGIE,
    SEUILS_GES,
    _classes_lot,
    ep_au_coefficient_lot,
    recalculer_lot,
)

RACINE = Path(__file__).resolve().parent.parent
ENTREE = RACINE / "data" / "dpe_paca.parquet"
SORTIE_JSON = RACINE / "reports" / "validation_etiquettes.json"
SORTIE_MD = RACINE / "reports" / "validation_etiquettes.md"

DATE_19 = pd.Timestamp("2026-01-01")
TRANCHES = [("< 40 m²", 0, 40), ("40–100 m²", 40, 100), ("> 100 m²", 100, np.inf)]
N_EXEMPLES = 15


def tranche_surface(surface: pd.Series) -> pd.Series:
    etiquettes = pd.Series("", index=surface.index)
    for nom, bas, haut in TRANCHES:
        etiquettes[(surface >= bas) & (surface < haut)] = nom
    return etiquettes


def comparer(df: pd.DataFrame, coefficient: float) -> dict:
    recalc = recalculer_lot(df, coefficient)
    vrai = df["etiquette_dpe"].astype(str)
    ok = recalc == vrai
    tranche = tranche_surface(df["surface_habitable_logement"])

    # Les deux composantes du double seuil, pour comprendre les écarts
    ep = ep_au_coefficient_lot(df, coefficient)
    c_ep = np.asarray(CLASSES)[_classes_lot(ep, SEUILS_ENERGIE)]
    c_ges = np.asarray(CLASSES)[_classes_lot(df["emission_ges_5_usages_par_m2"].to_numpy(float), SEUILS_GES)]
    # Écart de rang (réel − recalculé) : > 0 si le DPE officiel est plus mauvais
    ecart = vrai.map(CLASSES.index) - recalc.map(CLASSES.index)

    par_tranche = {}
    for nom, _, _ in TRANCHES:
        m = tranche == nom
        par_tranche[nom] = {"n": int(m.sum()), "concordance": float(ok[m].mean()) if m.any() else None}

    # Somme des consommations par énergie ≠ total : part électrique peut-être incomplète
    somme_n = df[[f"conso_5_usages_ef_energie_n{n}" for n in (1, 2, 3)]].fillna(0).sum(axis=1)
    incomplet = (somme_n - df["conso_5_usages_ef"]).abs() > 0.01 * df["conso_5_usages_ef"].abs()

    # Diagnostic des désaccords : petites surfaces, valeurs publiées pile sur un seuil
    petit = df["surface_habitable_logement"] < 40
    pile_sur_seuil = (df["conso_5_usages_par_m2_ep"].isin(SEUILS_ENERGIE)
                      | df["emission_ges_5_usages_par_m2"].isin(SEUILS_GES))
    diagnostic = {}
    for nom, m in (("< 40 m²", petit), (">= 40 m²", ~petit)):
        k = ~ok & m
        diagnostic[nom] = {
            "desaccords": int(k.sum()),
            "officiel_meilleur": int((k & (ecart < 0)).sum()),
            "officiel_plus_mauvais": int((k & (ecart > 0)).sum()),
            "valeur_ep_ou_ges_pile_sur_un_seuil": int((k & pile_sur_seuil).sum()),
        }
    bornes = [0, 10, 15, 20, 25, 30, 35, 40, 45, 50, np.inf]
    fine = pd.cut(df["surface_habitable_logement"], bornes, right=False)
    par_surface_fine = {str(k): {"n": int(g.size), "concordance": float(g.mean())}
                        for k, g in ok.groupby(fine, observed=True)}
    trimestre = pd.to_datetime(df["date_etablissement_dpe"]).dt.to_period("Q").astype(str)
    par_trimestre = {
        t: {"< 40 m²": float(ok[(trimestre == t) & petit].mean()),
            ">= 40 m²": float(ok[(trimestre == t) & ~petit].mean())}
        for t in sorted(trimestre.unique())
    }

    confusion = pd.crosstab(vrai, recalc).reindex(index=CLASSES, columns=CLASSES, fill_value=0)

    cols = ["numero_dpe", "date_etablissement_dpe", "surface_habitable_logement", "type_energie_principale_chauffage",
            "conso_5_usages_par_m2_ep", "emission_ges_5_usages_par_m2", "etiquette_dpe"]
    ex = df.loc[~ok, cols].copy()
    ex["ep_recalculee"] = ep[(~ok).to_numpy()]
    ex["classe_ep"] = c_ep[(~ok).to_numpy()]
    ex["classe_ges"] = c_ges[(~ok).to_numpy()]
    ex["etiquette_recalculee"] = recalc[~ok]
    ex = ex.sample(min(N_EXEMPLES, len(ex)), random_state=42) if len(ex) else ex
    ex["date_etablissement_dpe"] = ex["date_etablissement_dpe"].astype(str)

    return {
        "coefficient": coefficient,
        "n": int(len(df)),
        "concordance": float(ok.mean()),
        "par_tranche": par_tranche,
        "ecarts_par_rang": {str(int(k)): int(v) for k, v in ecart[~ok].value_counts().sort_index().items()},
        "diagnostic_desaccords": diagnostic,
        "concordance_par_surface_fine": par_surface_fine,
        "concordance_par_trimestre": par_trimestre,
        "concordance_composante_energie_seule": float((c_ep == vrai.to_numpy()).mean()),
        "consommations_par_energie_incompletes": {
            "n": int(incomplet.sum()),
            "concordance": float(ok[incomplet].mean()) if incomplet.any() else None,
        },
        "concordance_par_chauffage": {
            str(k): {"n": int(g.size), "concordance": float(g.mean())}
            for k, g in ok.groupby(df["type_energie_principale_chauffage"].astype(str))
        },
        "confusion_reel_lignes_recalcule_colonnes": confusion.values.tolist(),
        "exemples_ecarts": ex.to_dict(orient="records"),
    }


def _n(x) -> str:
    return f"{x:,}".replace(",", " ")


def _p(x) -> str:
    return "—" if x is None else f"{100 * x:.2f} %"


def section(titre: str, r: dict) -> str:
    lignes = [f"## {titre}", "",
              f"- DPE comparés : {_n(r['n'])}, coefficient {r['coefficient']}",
              f"- **Concordance globale : {_p(r['concordance'])}**",
              "", "| Tranche de surface | DPE | Concordance |", "|---|---:|---:|"]
    for nom, t in r["par_tranche"].items():
        lignes.append(f"| {nom} | {_n(t['n'])} | {_p(t['concordance'])} |")
    inc = r["consommations_par_energie_incompletes"]
    lignes += ["",
               f"Consommations par énergie dont la somme diffère du total de plus de 1 % : {_n(inc['n'])} DPE "
               f"(concordance {_p(inc['concordance'])}).", "",
               "Écart de rang réel − recalculé parmi les désaccords (> 0 : DPE officiel plus mauvais) : "
               + ", ".join(f"{k} : {_n(v)}" for k, v in r["ecarts_par_rang"].items()), "",
               "| Désaccords | Total | DPE officiel meilleur | DPE officiel plus mauvais | Valeur EP ou GES pile sur un seuil |",
               "|---|---:|---:|---:|---:|"]
    for nom, dg in r["diagnostic_desaccords"].items():
        lignes.append(f"| {nom} | {_n(dg['desaccords'])} | {_n(dg['officiel_meilleur'])} | "
                      f"{_n(dg['officiel_plus_mauvais'])} | {_n(dg['valeur_ep_ou_ges_pile_sur_un_seuil'])} |")
    lignes += ["", "| Surface (m²) | DPE | Concordance |", "|---|---:|---:|"]
    for k, v in r["concordance_par_surface_fine"].items():
        lignes.append(f"| {k} | {_n(v['n'])} | {_p(v['concordance'])} |")
    lignes += ["", "| Trimestre | Concordance < 40 m² | Concordance ≥ 40 m² |", "|---|---:|---:|"]
    for t, v in r["concordance_par_trimestre"].items():
        lignes.append(f"| {t} | {_p(v['< 40 m²'])} | {_p(v['>= 40 m²'])} |")
    lignes += ["", "| Chauffage principal | DPE | Concordance |", "|---|---:|---:|"]
    for k, v in sorted(r["concordance_par_chauffage"].items(), key=lambda kv: -kv[1]["n"]):
        lignes.append(f"| {k} | {_n(v['n'])} | {_p(v['concordance'])} |")
    lignes += ["", "Matrice réel (lignes) / recalculé (colonnes) :", "",
               "| | " + " | ".join(CLASSES) + " |", "|---|" + "---:|" * len(CLASSES)]
    for c, ligne in zip(CLASSES, r["confusion_reel_lignes_recalcule_colonnes"]):
        lignes.append(f"| **{c}** | " + " | ".join(_n(x) for x in ligne) + " |")
    if r["exemples_ecarts"]:
        lignes += ["", f"Exemples d'écarts (tirés au hasard, graine 42) :", "",
                   "| N° DPE | Date | Surface | Chauffage | EP DPE | EP recalc. | GES | Classe EP | Classe GES | Réel | Recalculé |",
                   "|---|---|---:|---|---:|---:|---:|---|---|---|---|"]
        for e in r["exemples_ecarts"]:
            lignes.append(
                f"| {e['numero_dpe']} | {e['date_etablissement_dpe'][:10]} | {e['surface_habitable_logement']:.1f} | "
                f"{e['type_energie_principale_chauffage']} | {e['conso_5_usages_par_m2_ep']:.1f} | {e['ep_recalculee']:.1f} | "
                f"{e['emission_ges_5_usages_par_m2']:.1f} | {e['classe_ep']} | {e['classe_ges']} | "
                f"{e['etiquette_dpe']} | {e['etiquette_recalculee']} |")
    return "\n".join(lignes)


def main() -> None:
    df = pd.read_parquet(ENTREE)
    dates = pd.to_datetime(df["date_etablissement_dpe"])
    res = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seuils_energie": SEUILS_ENERGIE,
        "seuils_ges": SEUILS_GES,
        "depuis_2026_coef_1_9": comparer(df[dates >= DATE_19], 1.9),
        "avant_2026_coef_2_3": comparer(df[dates < DATE_19], 2.3),
    }
    SORTIE_JSON.write_bytes(json.dumps(res, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    md = "\n\n".join([
        "# Validation du recalcul des étiquettes",
        f"Généré par `training/valider_etiquettes.py` le {res['genere_le']}. Seuils appliqués (double seuil, "
        f"bornes incluses) : énergie {SEUILS_ENERGIE} kWh/m²·an, GES {SEUILS_GES} kgCO₂/m²·an. "
        "Aucun seuil spécifique aux petites surfaces n'est appliqué.",
        section("DPE établis depuis le 2026-01-01, recalculés en 1,9", res["depuis_2026_coef_1_9"]),
        section("Contrôle : DPE établis avant 2026, recalculés en 2,3", res["avant_2026_coef_2_3"]),
    ]) + "\n"
    SORTIE_MD.write_bytes(md.encode("utf-8"))
    for cle in ("depuis_2026_coef_1_9", "avant_2026_coef_2_3"):
        r = res[cle]
        print(cle, _p(r["concordance"]), {k: _p(v["concordance"]) for k, v in r["par_tranche"].items()})


if __name__ == "__main__":
    main()
