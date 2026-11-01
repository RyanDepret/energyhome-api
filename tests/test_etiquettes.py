import pandas as pd
import pytest

from training.etiquettes import (
    classe_selon_seuils,
    ef_electrique_par_m2,
    recalculer_etiquette,
    recalculer_lot,
    SEUILS_ENERGIE,
)


def dpe(**champs):
    base = {
        "date_etablissement_dpe": "2024-03-01",
        "surface_habitable_logement": 50.0,
        "conso_5_usages_par_m2_ep": 200.0,
        "emission_ges_5_usages_par_m2": 5.0,
        "type_energie_n1": "Électricité",
        "conso_5_usages_ef_energie_n1": 2500.0,  # 50 kWh/m²
        "type_energie_n2": None,
        "conso_5_usages_ef_energie_n2": None,
        "type_energie_n3": None,
        "conso_5_usages_ef_energie_n3": None,
    }
    return {**base, **champs}


@pytest.mark.parametrize("valeur, attendu", [(70, "A"), (70.1, "B"), (180, "C"), (420, "F"), (421, "G")])
def test_seuils_bornes_incluses(valeur, attendu):
    assert classe_selon_seuils(valeur, SEUILS_ENERGIE) == attendu


def test_ef_electrique_ne_compte_que_l_electricite():
    ligne = dpe(type_energie_n2="Gaz naturel", conso_5_usages_ef_energie_n2=5000.0)
    assert ef_electrique_par_m2(ligne) == pytest.approx(50.0)


def test_ef_electrique_inclut_electricite_renouvelable():
    ligne = dpe(
        type_energie_n2="Électricité d'origine renouvelable utilisée dans le bâtiment",
        conso_5_usages_ef_energie_n2=500.0,
    )
    assert ef_electrique_par_m2(ligne) == pytest.approx(60.0)


def test_passage_23_vers_19():
    # 200 − (2,3 − 1,9) × 50 = 180 → C (était D)
    assert recalculer_etiquette(dpe(), 2.3) == "D"
    assert recalculer_etiquette(dpe(), 1.9) == "C"


def test_dpe_deja_en_19_inchange():
    ligne = dpe(date_etablissement_dpe="2026-02-01")
    assert recalculer_etiquette(ligne, 1.9) == "D"
    # vers 1,7 : 200 − 0,2 × 50 = 190 → toujours D
    assert recalculer_etiquette(ligne, 1.7) == "D"


def test_ges_peut_imposer_la_classe():
    assert recalculer_etiquette(dpe(emission_ges_5_usages_par_m2=60.0), 1.9) == "E"


def test_sans_electricite_inchange():
    ligne = dpe(type_energie_n1="Gaz naturel")
    assert recalculer_etiquette(ligne, 1.9) == "D"


def test_date_trop_ancienne_refusee():
    with pytest.raises(ValueError):
        recalculer_etiquette(dpe(date_etablissement_dpe="2021-06-30"), 1.9)


def test_lot_identique_a_la_ligne():
    lignes = [
        dpe(),
        dpe(date_etablissement_dpe="2026-02-01"),
        dpe(emission_ges_5_usages_par_m2=60.0),
        dpe(type_energie_n1="Gaz naturel"),
        dpe(conso_5_usages_par_m2_ep=70.0, conso_5_usages_ef_energie_n1=None),
        dpe(conso_5_usages_par_m2_ep=500.0, emission_ges_5_usages_par_m2=6.0),
    ]
    df = pd.DataFrame(lignes)
    attendu = [recalculer_etiquette(l, 1.9) for l in lignes]
    assert recalculer_lot(df, 1.9).tolist() == attendu
