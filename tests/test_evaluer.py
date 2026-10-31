"""Métriques de l'évaluation et équivalence des features avec l'API."""

import itertools

import numpy as np
import pandas as pd
import pytest

from app.ml.features import build_features
from app.ml.model import get_columns
from app.schemas.predict import CHAUFFAGE_LABELS, PERIODE_LABELS, TYPE_BATIMENT_LABELS
from training import evaluer as ev


@pytest.mark.parametrize(
    "vrai, pred, attendu",
    [
        (["C"], ["C"], 1.0),
        (["C"], ["B"], 1.0),
        (["C"], ["D"], 1.0),
        (["C"], ["A"], 0.0),
        (["C"], ["E"], 0.0),
        (["A"], ["G"], 0.0),
        (["A", "D", "G", "B"], ["B", "F", "G", "D"], 0.5),
    ],
)
def test_accuracy_a_une_classe_pres(vrai, pred, attendu):
    assert ev.accuracy_a_une_classe_pres(vrai, pred) == attendu


def test_brier_multiclasse():
    parfait = np.eye(7)[[0, 3]]
    assert ev.brier_multiclasse(["A", "D"], parfait) == 0.0
    assert ev.brier_multiclasse(["A"], np.eye(7)[[1]]) == 2.0  # sûr et faux
    uniforme = np.full((1, 7), 1 / 7)
    assert ev.brier_multiclasse(["C"], uniforme) == pytest.approx(6 / 7)


def test_fiabilite_par_tranches():
    probas = np.zeros((3, 7))
    probas[0, 0] = 0.95  # annonce A à 95 %, juste
    probas[1, 1] = 0.92  # annonce B à 92 %, faux
    probas[2, 2] = 0.35  # annonce C à 35 %, juste
    tranches = ev.fiabilite(["A", "C", "C"], probas)
    assert tranches[9] == {"tranche": "90–100 %", "effectif": 2, "probabilite_moyenne_annoncee": pytest.approx(0.935),
                           "taux_bonnes_reponses": 0.5}
    assert tranches[3]["effectif"] == 1 and tranches[3]["taux_bonnes_reponses"] == 1.0
    assert tranches[0]["effectif"] == 0 and tranches[0]["taux_bonnes_reponses"] is None


def test_features_en_lot_identiques_a_build_features():
    colonnes = get_columns()
    combinaisons = list(itertools.product(PERIODE_LABELS, TYPE_BATIMENT_LABELS, CHAUFFAGE_LABELS, ["H2d", "H3"]))
    entrees = pd.DataFrame(combinaisons, columns=["periode", "type_batiment", "chauffage", "zone_climatique_api"])
    surfaces = np.linspace(9, 1000, len(entrees))
    X = ev.features_en_lot(surfaces, entrees, colonnes)
    for i, (p, t, c, z) in enumerate(combinaisons):
        attendu = build_features(float(surfaces[i]), p, t, c, z, colonnes)
        assert np.array_equal(attendu.to_numpy(dtype=float)[0], X.iloc[i].to_numpy())


def test_preparer_entrees_exclut_ce_que_l_api_refuse():
    df = pd.DataFrame({
        "periode_construction": ["1948-1974", "1948-1974", "inconnue", "1948-1974"],
        "type_batiment": ["maison", "appartement", "maison", "maison"],
        "type_energie_principale_chauffage": ["Gaz naturel", "Charbon", "Gaz naturel", "Électricité"],
        "code_departement_ban": ["13", "13", "13", "75"],
    })
    entrees, exclusions = ev.preparer_entrees(df)
    assert entrees.index.tolist() == [0]
    assert exclusions == {"periode_inconnue": 1, "type_batiment_inconnu": 0, "chauffage_inconnu": 1,
                          "departement_sans_zone": 1, "total_lignes_exclues": 3}


def _dpe(date, etiquette, chauffage="Gaz naturel"):
    return {"date_etablissement_dpe": date, "etiquette_dpe": etiquette, "surface_habitable_logement": 70.0,
            "periode_construction": "1948-1974", "type_batiment": "appartement",
            "type_energie_principale_chauffage": chauffage, "code_departement_ban": "13", "zone_climatique": "H3"}


def test_evaluer_test_temporel_et_references():
    df = pd.DataFrame(
        [_dpe("2025-03-01", "D")] * 3 + [_dpe("2025-04-01", "C")]          # avant coupure : D majoritaire
        + [_dpe("2026-09-15", "D"), _dpe("2026-10-01", "E", "Électricité"),
           _dpe("2026-10-02", "C", "Charbon")]                              # test (Charbon exclu)
    )
    res = ev.evaluer(df, "2026-08-30")
    assert res["avant_coupure"] == 4 and res["test_brut"] == 3 and res["test_evalue"] == 2
    assert res["references"]["classe_majoritaire"] == "D"
    tous = res["resultats"]["tous"]
    assert tous["classe_majoritaire"]["accuracy"] == 0.5
    assert tous["modele"]["effectif"] == 2
    assert res["resultats"]["chauffage_electrique"]["modele"]["effectif"] == 1
    assert res["coefficient_electricite_1_9"] == {"test_total": 2, "etablis_depuis_2026_01_01": 2,
                                                  "dont_chauffage_electrique": 1, "dont_autres_chauffages": 1}
    assert "Le modèle actuel" in ev.phrase_verdict(tous)
