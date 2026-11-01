"""Artefacts v3 : cohérence, explications rapides et conformes au contrat du front."""

import json
import time

import pytest

from app.core.config import settings
from app.ml import modele_v3


@pytest.fixture(scope="module")
def artefact():
    return modele_v3.charger(settings.model_v3_dir)


ENTREE = {"surface": 45.0, "periode": "1948_1974", "type_batiment": "appartement", "chauffage": "electricite",
          "departement": "06", "zone_climatique": "H3"}


def test_metadonnees_completes(artefact):
    meta = artefact["metadonnees"]
    for cle in ("version", "date_export", "coefficient_electricite_cible", "donnees", "metriques_test", "bibliotheques"):
        assert cle in meta
    assert meta["coefficient_electricite_cible"] == 1.9
    assert len(meta["donnees"]["sha256_entrainement"]) == 64
    assert meta["colonnes"] == json.loads((settings.model_v3_dir / "colonnes.json").read_text(encoding="utf-8"))


def test_probabilites_calibrees_somment_a_un(artefact):
    _, probas, _ = modele_v3.predire(artefact, ENTREE)
    assert list(probas) == modele_v3.CLASSES_DPE
    assert sum(probas.values()) == pytest.approx(1.0)


def test_expliquer_contrat_front(artefact):
    facteurs = modele_v3.expliquer(artefact, ENTREE)
    assert all(set(f) == {"critere", "valeur", "poids"} for f in facteurs)
    assert all(0 <= f["poids"] <= 1 for f in facteurs)
    assert sum(f["poids"] for f in facteurs) == pytest.approx(1.0)


def test_expliquer_rapide(artefact):
    modele_v3.expliquer(artefact, ENTREE)
    t0 = time.perf_counter()
    for _ in range(20):
        modele_v3.predire(artefact, ENTREE)
    assert (time.perf_counter() - t0) / 20 < 0.2  # < 200 ms par prédiction expliquée


def test_charbon_connu_du_modele_mais_pas_de_l_api(artefact):
    # Le modèle sait encoder le charbon (données d'entraînement), /predict le refuse (test_predict)
    _, probas, _ = modele_v3.predire(artefact, {**ENTREE, "chauffage": "charbon"})
    assert sum(probas.values()) == pytest.approx(1.0)
