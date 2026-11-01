"""Fiche du modèle v3 (reports/fiche_modele_v3.md), générée à partir des rapports JSON.

Aucun chiffre n'est écrit à la main : tout vient de reports/*.json et artifacts/v3/metadonnees.json.

Usage : .venv/Scripts/python.exe -m training.fiche_v3
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

CLASSES = ["A", "B", "C", "D", "E", "F", "G"]

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "reports" / "fiche_modele_v3.md"


def lire(chemin: str) -> dict:
    return json.loads((RACINE / chemin).read_text(encoding="utf-8"))


def _n(x) -> str:
    return f"{x:,}".replace(",", " ")


def _p(x) -> str:
    return f"{100 * x:.1f} %"


# Au-delà de ces écarts entre l'entraînement et le moins bon des jeux non vus, on signale un sur-apprentissage
SEUIL_ECART_ACCURACY = 0.02
SEUIL_ECART_BRIER = 0.02


def section_ecart(e: dict) -> list[str]:
    """Tableau entraînement / validation / test et conclusion tirée des chiffres (aucun texte figé sur le verdict)."""
    c, lg = e["calibre"], e["lignes"]
    jeux = ("entrainement", "validation", "test")
    l = ["## Écart entre entraînement, validation et test", "",
         f"| | Entraînement ({_n(lg['entrainement'])}) | Validation ({_n(lg['validation'])}) | Test ({_n(lg['test'])}) |",
         "|---|---:|---:|---:|"]
    for cle, lib, f in (("accuracy", "Accuracy", _p), ("accuracy_a_une_classe_pres", "Accuracy à une classe près", _p),
                        ("brier_multiclasse", "Brier multiclasse (plus bas = mieux)", lambda v: f"{v:.4f}")):
        l.append(f"| {lib} | " + " | ".join(f(c[j][cle]) for j in jeux) + " |")

    ecart_acc = c["entrainement"]["accuracy"] - min(c["validation"]["accuracy"], c["test"]["accuracy"])
    ecart_brier = max(c["validation"]["brier_multiclasse"], c["test"]["brier_multiclasse"]) - c["entrainement"]["brier_multiclasse"]
    chiffres = (f"l'accuracy d'entraînement dépasse celle du moins bon jeu non vu de {100 * ecart_acc:.1f} point(s) "
                f"et le Brier est plus élevé de {ecart_brier:.3f} hors entraînement")
    if ecart_acc <= SEUIL_ECART_ACCURACY and ecart_brier <= SEUIL_ECART_BRIER:
        conclusion = (f"Pas de sur-apprentissage mesurable : {chiffres}. Le modèle ne fait guère mieux sur les logements "
                      f"qu'il a vus ({_p(c['entrainement']['accuracy'])} d'accuracy) que sur les autres : sa précision est "
                      "limitée par l'information contenue dans les cinq variables, pas par un apprentissage par cœur.")
    else:
        conclusion = (f"**Sur-apprentissage** : {chiffres} (seuils : {100 * SEUIL_ECART_ACCURACY:.0f} points, "
                      f"{SEUIL_ECART_BRIER:.2f} de Brier). Les résultats sur l'entraînement surestiment ceux attendus en service.")
    b = e["brut"]
    l += ["", conclusion, "",
          "Mesures : entraînement calculé par `training/ecart_v3.py` avec le modèle servi (calibration comprise) ; "
          "validation avec la calibration isotonique mesurée hors pli (`reports/calibration_v3.md`) ; test repris de "
          "`reports/modele_v3.md`. La validation a servi à l'arrêt précoce, au choix du modèle et à la calibration. "
          f"Sans calibration : Brier {b['entrainement']['brier_multiclasse']:.4f} sur l'entraînement contre "
          f"{b['validation']['brier_multiclasse']:.4f} sur la validation.", ""]
    return l


def main() -> None:
    meta = lire("artifacts/v3/metadonnees.json")
    donnees = lire("reports/donnees_v3.json")
    comp = lire("reports/comparaison_v3.json")
    calib = lire("reports/calibration_v3.json")
    test = lire("reports/modele_v3.json")
    expl = lire("reports/explications_v3.json")
    val = lire("reports/validation_etiquettes.json")

    j = donnees["jeux"]
    tous = test["resultats"]["tous"]
    courbe = calib["courbe_apprentissage"]
    imp = sorted(expl["importance_globale"].values(), key=lambda v: -v["part_classe_predite"])
    conf = np.array(tous["v3"]["matrice_confusion"])
    pred_efg, reel_efg = int(conf[:, 4:].sum()), int(conf[4:, :].sum())
    moins_bien = [c for c in CLASSES if tous["v3"]["f1_par_classe"][c] < tous["v1"]["f1_par_classe"][c]]
    oui = lambda b: "oui" if b else "**non**"  # noqa: E731

    lignes = [
        "# Fiche du modèle v3 — estimation de la classe DPE", "",
        f"Version `{meta['version']}`, exportée le {meta['date_export'][:10]}. "
        "Fiche générée par `training/fiche_v3.py` à partir des rapports du dépôt.", "",
        "## Usage prévu", "",
        "Donner une **estimation indicative** de la classe DPE (A à G) d'un logement de la région PACA à partir de "
        "cinq informations que tout le monde connaît. **Ce n'est pas un DPE officiel** : un DPE est établi par un "
        "diagnostiqueur certifié qui visite le logement.", "",
        "## Données", "",
        f"- Source : ADEME, base publique des DPE de logements existants (`dpe03existant`), région PACA, "
        f"maisons et appartements.",
        f"- Entraînement : {_n(j['entrainement']['lignes'])} DPE établis du {j['entrainement']['du']} au {j['entrainement']['au']}.",
        f"- Validation (choix du modèle, des réglages et de la calibration) : {_n(j['validation']['lignes'])} DPE "
        f"du {j['validation']['du']} au {j['validation']['au']}.",
        f"- Test (utilisé une seule fois, à la fin) : {_n(j['test']['lignes'])} DPE du {j['test']['du']} au {j['test']['au']}, "
        "identique à celui de la mesure du modèle précédent.",
        f"- Empreinte SHA-256 des données d'entraînement : `{meta['donnees']['sha256_entrainement'][:16]}…`.", "",
        "## Variables", "",
        "Uniquement ce que l'utilisateur saisit : surface, période de construction, type de bâtiment, énergie de "
        "chauffage et département (déduit du code postal). Aucune consommation, émission ni étiquette en entrée. "
        "La zone climatique, entièrement déterminée par le département, n'apporte rien de plus "
        "(`reports/comparaison_v3.md`).", "",
        "Importance moyenne dans les prédictions (contributions SHAP, validation) : " +
        ", ".join(f"{v['critere'].lower()} {_p(v['part_classe_predite'])}" for v in imp) + ".", "",
        "## Cible", "",
        f"L'étiquette DPE officielle (`etiquette_dpe`), au coefficient électricité {donnees['coefficient_cible']}. "
        f"Le jeu ADEME publie déjà tous les DPE à ce coefficient, y compris ceux établis avant 2026 (rapport énergie "
        f"primaire / finale médian des logements tout électriques : {donnees['controle_coefficient_publie']['mediane']:.3f}) ; "
        "ce coefficient est contrôlé automatiquement à chaque préparation des données. Les seuils officiels "
        f"(petites surfaces, altitude) reproduisent {100 * val['depuis_2026_coef_1_9']['concordance']:.2f} % des étiquettes 2026.", "",
        "## Modèle", "",
        f"{comp['choix']}, choisi sur la validation parmi {len(comp['resultats'])} candidats (références, régression "
        f"logistique, Random Forest, LightGBM, approche ordinale) ; calibration : {calib['methode_retenue']}. "
        f"Fichier du modèle : {next(r['taille_mo'] for r in comp['resultats'] if r['nom'] == comp['choix']):.1f} Mo.", "",
        "## Résultats sur le test", "",
        "| | Modèle v3 | Modèle précédent (v1) | Toujours « " + tous["classe_majoritaire_nom"] + " » | Répartition constante |",
        "|---|---:|---:|---:|---:|",
        f"| Accuracy | {_p(tous['v3']['accuracy'])} | {_p(tous['v1']['accuracy'])} | {_p(tous['classe_majoritaire']['accuracy'])} | — |",
        f"| Accuracy à une classe près | {_p(tous['v3']['accuracy_a_une_classe_pres'])} | "
        f"{_p(tous['v1']['accuracy_a_une_classe_pres'])} | {_p(tous['classe_majoritaire']['accuracy_a_une_classe_pres'])} | — |",
        f"| F1 macro | {_p(tous['v3']['f1_macro'])} | {_p(tous['v1']['f1_macro'])} | {_p(tous['classe_majoritaire']['f1_macro'])} | — |",
        f"| Brier multiclasse (plus bas = mieux) | {tous['v3']['brier_multiclasse']:.3f} | {tous['v1']['brier_multiclasse']:.3f} | — | "
        f"{tous['brier_reference_repartition_constante']:.3f} |", "",
        f"Bat « toujours {tous['classe_majoritaire_nom']} » en accuracy : {oui(tous['verdicts']['accuracy_vs_classe_majoritaire'])} ; "
        f"à une classe près : {oui(tous['verdicts']['a_une_classe_pres_vs_classe_majoritaire'])} ; "
        f"la répartition constante en Brier : {oui(tous['verdicts']['brier_vs_repartition_constante'])}. "
        "Détail par type de chauffage : `reports/modele_v3.md`.", "",
        *section_ecart(lire("reports/ecart_v3.json")),
        "## Limites connues", "",
        "- **Cinq variables seulement** : l'isolation, les fenêtres, le système de chauffage exact, la ventilation ou "
        "les travaux ne sont pas observés. Deux logements identiques sur ces cinq critères reçoivent la même estimation "
        "alors que leurs DPE réels peuvent différer ; c'est la principale limite de précision.",
        f"- **Classes extrêmes rarement prédites** : sur le test, le modèle prédit E, F ou G pour {_n(pred_efg)} logements "
        f"alors que {_n(reel_efg)} le sont réellement ; il tire les estimations vers C et D. "
        + (f"Le F1 est plus faible que celui du v1 pour les classes {', '.join(moins_bien)} (le v1 prédisait beaucoup "
           "plus souvent les classes extrêmes, à tort dans la plupart des cas)." if moins_bien else ""),
        "- **PACA uniquement** : le modèle n'a vu aucun logement d'une autre région.",
        "- Courbe d'apprentissage (Brier de validation) : " + ", ".join(
            f"{_n(c['lignes'])} lignes → {c['brier_multiclasse']:.3f}" for c in courbe) + ". "
        + ("Le Brier ne s'améliore plus au-delà de " + _n(courbe[-2]['lignes']) + " lignes : plus de logements décrits "
           "par les mêmes cinq variables (France métropolitaine) aideraient peu ; d'autres variables aideraient davantage."
           if courbe[-1]['brier_multiclasse'] >= courbe[-2]['brier_multiclasse'] - 0.002
           else "Le Brier s'améliore encore : plus de données (France métropolitaine) pourraient aider."),
        "- Altitude : non demandée à l'utilisateur ; les seuils spécifiques au-dessus de 800 m (Hautes-Alpes, "
        "Alpes-de-Haute-Provence) ne sont appris qu'à travers le département.",
        "- Chauffages rares (charbon, plaquettes, butane) : peu d'exemples, estimations moins fiables.",
        "- Le coefficient électricité passe à 1,7 au 1er janvier 2027 : le modèle devra être réentraîné "
        "(cible recalculable par `training/etiquettes.py`).", "",
    ]
    SORTIE.write_bytes("\n".join(lignes).encode("utf-8"))
    print(f"Fiche écrite : {SORTIE}")


if __name__ == "__main__":
    main()
