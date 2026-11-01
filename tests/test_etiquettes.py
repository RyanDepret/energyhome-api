import numpy as np
import pandas as pd
import pytest

from app.core.reglementation import (
    TABLE_PETITES_SURFACES,
    TABLE_PETITES_SURFACES_ALTITUDE,
    seuils_etiquette,
)
from training.etiquettes import (
    classe_selon_seuils,
    ef_electrique_par_m2,
    etiquette_cible,
    recalculer_etiquette,
    recalculer_lot,
    seuils_lot,
)

STANDARD = (70, 110, 180, 250, 330, 420)


def dpe(**champs):
    base = {
        "date_etablissement_dpe": "2024-09-01",
        "surface_habitable_logement": 50.0,
        "conso_5_usages_par_m2_ep": 200.0,
        "emission_ges_5_usages_par_m2": 5.0,
        "type_energie_n1": "Électricité",
        "conso_5_usages_ef_energie_n1": 2500.0,  # 50 kWh/m²
        "type_energie_n2": None,
        "conso_5_usages_ef_energie_n2": None,
        "type_energie_n3": None,
        "conso_5_usages_ef_energie_n3": None,
        "zone_climatique": "H3",
        "classe_altitude": "inférieur à 400m",
        "etiquette_dpe": "D",
    }
    return {**base, **champs}


# ── Règle officielle : arrondi inférieur et inégalités strictes ─────────────

@pytest.mark.parametrize(
    "valeur, attendu",
    [(69, "A"), (69.9, "A"), (70, "B"), (70.4, "B"), (179.99, "C"), (180, "D"), (419, "F"), (420, "G")],
)
def test_seuils_stricts_apres_arrondi_inferieur(valeur, attendu):
    assert classe_selon_seuils(valeur, STANDARD) == attendu


# ── Tableaux de l'arrêté du 25 mars 2024 ────────────────────────────────────

def test_tables_recopiees_completes():
    assert [l[0] for l in TABLE_PETITES_SURFACES] == list(range(8, 41))
    assert [l[0] for l in TABLE_PETITES_SURFACES_ALTITUDE] == list(range(8, 41))
    # Quelques valeurs relues dans le Journal officiel
    assert TABLE_PETITES_SURFACES[0] == (8, 146, 11, 186, 16, 386, 44, 505, 68, 622, 90, 739, 122)
    assert TABLE_PETITES_SURFACES[13] == (21, 87, 8, 127, 13, 225, 33, 295, 53, 380, 74, 471, 104)
    assert TABLE_PETITES_SURFACES_ALTITUDE[0] == (8, 682, 100, 819, 132)
    # À 40 m², la table rejoint les seuils standards
    assert TABLE_PETITES_SURFACES[-1][1:] == (70, 6, 110, 11, 180, 30, 250, 50, 330, 70, 420, 100)
    assert TABLE_PETITES_SURFACES_ALTITUDE[-1][1:] == (390, 80, 500, 110)


def test_interpolation_lineaire_et_bornes():
    cep, eges = seuils_etiquette(21.5)
    assert cep[0] == pytest.approx((87 + 85) / 2)
    assert eges[2] == pytest.approx(33)
    assert seuils_etiquette(5) == seuils_etiquette(8)  # « ≤ 8 »
    assert seuils_etiquette(40.5)[0] == list(STANDARD)


def test_altitude_seulement_en_h1b_h1c_h2d():
    assert seuils_etiquette(60, True, "H1c")[0][4:] == [390, 500]
    assert seuils_etiquette(60, True, "H3")[0][4:] == [330, 420]
    assert seuils_etiquette(60, False, "H1c")[0][4:] == [330, 420]
    cep, eges = seuils_etiquette(8, True, "H2d")
    assert (cep[4], eges[4], cep[5], eges[5]) == (682, 100, 819, 132)


def test_seuils_sans_petites_surfaces():
    assert seuils_etiquette(20, petites_surfaces=False)[0] == list(STANDARD)


# ── Recalcul ────────────────────────────────────────────────────────────────

def test_ef_electrique_ne_compte_que_l_electricite():
    ligne = dpe(type_energie_n2="Gaz naturel", conso_5_usages_ef_energie_n2=5000.0)
    assert ef_electrique_par_m2(ligne) == pytest.approx(50.0)


def test_ef_electrique_inclut_electricite_renouvelable():
    ligne = dpe(type_energie_n2="Électricité d'origine renouvelable utilisée dans le bâtiment",
                conso_5_usages_ef_energie_n2=500.0)
    assert ef_electrique_par_m2(ligne) == pytest.approx(60.0)


def test_passage_23_vers_19():
    # 200 − (2,3 − 1,9) × 50 = 180 → D (180 n'est pas < 180) ; 210 − 20 = 190 → D
    assert recalculer_etiquette(dpe(), 2.3) == "D"
    assert recalculer_etiquette(dpe(conso_5_usages_par_m2_ep=199.0), 1.9) == "C"


def test_petite_surface():
    # 21 m² : CEP_c = 225 → 200 est en C (D avec les seuils standards)
    ligne = dpe(surface_habitable_logement=21.0, conso_5_usages_ef_energie_n1=0.0)
    assert recalculer_etiquette(ligne, 2.3) == "C"
    assert recalculer_etiquette(ligne, 2.3, petites_surfaces=False) == "D"


def test_altitude():
    ligne = dpe(conso_5_usages_par_m2_ep=350.0, zone_climatique="H1c", classe_altitude="supérieur à 800m",
                conso_5_usages_ef_energie_n1=0.0)
    assert recalculer_etiquette(ligne, 2.3) == "E"
    assert recalculer_etiquette({**ligne, "classe_altitude": "400-800m"}, 2.3) == "F"


def test_ges_peut_imposer_la_classe():
    assert recalculer_etiquette(dpe(emission_ges_5_usages_par_m2=60.0), 1.9) == "E"


def test_date_trop_ancienne_refusee():
    with pytest.raises(ValueError):
        recalculer_etiquette(dpe(date_etablissement_dpe="2021-06-30"), 1.9)


LIGNES = [
    dpe(),
    dpe(date_etablissement_dpe="2026-02-01"),
    dpe(emission_ges_5_usages_par_m2=60.0),
    dpe(type_energie_n1="Gaz naturel"),
    dpe(conso_5_usages_par_m2_ep=70.0, conso_5_usages_ef_energie_n1=None),
    dpe(conso_5_usages_par_m2_ep=500.0, emission_ges_5_usages_par_m2=6.0),
    dpe(surface_habitable_logement=21.3, conso_5_usages_ef_energie_n1=800.0),
    dpe(surface_habitable_logement=7.0, conso_5_usages_par_m2_ep=640.0),
    dpe(surface_habitable_logement=30.0, conso_5_usages_par_m2_ep=420.0, zone_climatique="H2d",
        classe_altitude="supérieur à 800m"),
    dpe(conso_5_usages_par_m2_ep=400.0, zone_climatique="H1b", classe_altitude="supérieur à 800m"),
]


@pytest.mark.parametrize("petites_surfaces", [True, False])
def test_lot_identique_a_la_ligne(petites_surfaces):
    df = pd.DataFrame(LIGNES)
    attendu = [recalculer_etiquette(l, 1.9, petites_surfaces) for l in LIGNES]
    assert recalculer_lot(df, 1.9, petites_surfaces).tolist() == attendu


def test_seuils_lot_identiques_a_seuils_etiquette():
    df = pd.DataFrame(LIGNES)
    cep, eges = seuils_lot(df)
    for i, l in enumerate(LIGNES):
        c, e = seuils_etiquette(l["surface_habitable_logement"], l["classe_altitude"] == "supérieur à 800m",
                                l["zone_climatique"])
        np.testing.assert_allclose(cep[i], c)
        np.testing.assert_allclose(eges[i], e)


# ── Cible : étiquette officielle décalée du seul effet du coefficient ───────

def test_cible_garde_l_etiquette_officielle_sans_effet_du_coefficient():
    # Officiel « C » alors que le recalcul donne D : le coefficient ne change rien → C conservé
    df = pd.DataFrame([dpe(conso_5_usages_ef_energie_n1=0.0, etiquette_dpe="C")])
    assert etiquette_cible(df, 1.9).tolist() == ["C"]


def test_cible_applique_le_decalage_du_coefficient():
    # 2,3 → 1,9 : 200 → 180 reste D ; 205 → 185 reste D ; 190 → 170 passe de D à C
    df = pd.DataFrame([dpe(conso_5_usages_par_m2_ep=190.0, etiquette_dpe="E")])
    assert etiquette_cible(df, 1.9).tolist() == ["D"]


def test_cible_dpe_deja_au_coefficient_cible_inchangee():
    df = pd.DataFrame([dpe(date_etablissement_dpe="2026-03-01", etiquette_dpe="B")])
    assert etiquette_cible(df, 1.9).tolist() == ["B"]


def test_cible_bornee():
    df = pd.DataFrame([dpe(conso_5_usages_par_m2_ep=75.0, conso_5_usages_ef_energie_n1=3000.0,
                           emission_ges_5_usages_par_m2=1.0, etiquette_dpe="A")])
    assert etiquette_cible(df, 1.9).tolist() == ["A"]
