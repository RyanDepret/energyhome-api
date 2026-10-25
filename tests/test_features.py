from datetime import date
from itertools import product

import pytest
import sklearn

from app.core.config import settings
from app.ml import model
from app.ml.features import (
    CATEGORICAL_PREFIXES,
    FeatureError,
    annee_vers_periode,
    build_features,
    categorical_columns,
)
from app.schemas.predict import (
    CHAUFFAGE_LABELS,
    PERIODE_LABELS,
    TYPE_BATIMENT_LABELS,
    Chauffage,
    Periode,
    TypeBatiment,
)

COLONNES = model.get_columns()
ZONES_PACA = sorted({model.zone_climatique(dep) for dep in settings.departements_autorises})


def test_version_sklearn_identique_a_celle_du_modele():
    assert sklearn.__version__ == "1.9.0"


def test_chaque_annee_donne_une_colonne_existante():
    for annee in range(1800, date.today().year + 1):
        colonne = CATEGORICAL_PREFIXES["periode"] + PERIODE_LABELS[annee_vers_periode(annee)]
        assert colonne in COLONNES, f"{annee} → {colonne}"


@pytest.mark.parametrize(
    "annee, attendu",
    [
        (1800, Periode.AVANT_1948), (1947, Periode.AVANT_1948),
        (1948, Periode.P_1948_1974), (1974, Periode.P_1948_1974),
        (1975, Periode.P_1975_1977), (1977, Periode.P_1975_1977),
        (1978, Periode.P_1978_1982), (1982, Periode.P_1978_1982),
        (1983, Periode.P_1983_1988), (1988, Periode.P_1983_1988),
        (1989, Periode.P_1989_2000), (2000, Periode.P_1989_2000),
        (2001, Periode.P_2001_2005), (2005, Periode.P_2001_2005),
        (2006, Periode.P_2006_2012), (2012, Periode.P_2006_2012),
        (2013, Periode.P_2013_2021), (2021, Periode.P_2013_2021),
        (2022, Periode.APRES_2021),
    ],
)
def test_bornes_des_periodes(annee, attendu):
    assert annee_vers_periode(annee) == attendu


@pytest.mark.parametrize("periode", list(Periode))
def test_chaque_periode_existe_dans_le_modele(periode):
    assert CATEGORICAL_PREFIXES["periode"] + PERIODE_LABELS[periode] in COLONNES


@pytest.mark.parametrize("chauffage", list(Chauffage))
def test_chaque_chauffage_existe_dans_le_modele(chauffage):
    assert CATEGORICAL_PREFIXES["chauffage"] + CHAUFFAGE_LABELS[chauffage] in COLONNES


@pytest.mark.parametrize("type_batiment", list(TypeBatiment))
def test_chaque_type_batiment_existe_dans_le_modele(type_batiment):
    assert CATEGORICAL_PREFIXES["type_batiment"] + TYPE_BATIMENT_LABELS[type_batiment] in COLONNES


@pytest.mark.parametrize("departement", settings.departements_autorises)
def test_chaque_departement_autorise_a_une_zone_du_modele(departement):
    zone = model.zone_climatique(departement)
    assert CATEGORICAL_PREFIXES["zone_climatique"] + zone in COLONNES


def test_une_seule_colonne_activee_par_variable_categorielle():
    for periode, type_batiment, chauffage, zone in product(Periode, TypeBatiment, Chauffage, ZONES_PACA):
        ligne = build_features(80, periode, type_batiment, chauffage, zone, COLONNES).iloc[0]
        assert list(ligne.index) == COLONNES
        assert ligne["surface_habitable_logement"] == 80
        for prefixe in CATEGORICAL_PREFIXES.values():
            actives = [col for col in COLONNES if col.startswith(prefixe) and ligne[col] == 1]
            assert len(actives) == 1, (prefixe, actives)
        # Les colonnes activées sont exactement celles attendues
        attendues = categorical_columns(periode, type_batiment, chauffage, zone).values()
        assert all(ligne[col] == 1 for col in attendues)


def test_colonne_inexistante_leve_une_erreur():
    # Reproduit l'ancien bug (colonne « 1975-2000 » absente) : la colonne demandée n'existe pas
    colonnes_sans_periode = [c for c in COLONNES if c != "periode_construction_1975-1977"]
    with pytest.raises(FeatureError):
        build_features(80, Periode.P_1975_1977, TypeBatiment.MAISON, Chauffage.GAZ_NATUREL, "H3", colonnes_sans_periode)
    with pytest.raises(FeatureError):
        build_features(80, Periode.P_1975_1977, TypeBatiment.MAISON, Chauffage.GAZ_NATUREL, "H9", COLONNES)
