"""Téléchargement ADEME : pagination, reprise, nouvelles tentatives et estimation métropole (sans réseau)."""

import json
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest
import requests

from training import telecharger_dpe as td


class FausseReponse:
    def __init__(self, corps=None, statut=200, entetes=None):
        self.status_code = statut
        self._corps = corps if corps is not None else {}
        self.content = json.dumps(self._corps).encode("utf-8")
        self.text = self.content.decode("utf-8")
        self.headers = entetes or {}

    def json(self):
        return self._corps

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def ligne(i):
    return {"numero_dpe": f"DPE{i:04d}", "etiquette_dpe": "D", "surface_habitable_logement": 50 + i,
            "type_batiment": "maison", "_score": None}


class FausseAPI:
    """Simule /lines paginé par `next` ; peut couper la connexion à un appel donné."""

    def __init__(self, nb_lignes=25, taille=10, coupure_a=None, erreurs_transitoires=None):
        self.lignes = [ligne(i) for i in range(nb_lignes)]
        self.taille = taille
        self.coupure_a = coupure_a
        self.erreurs = list(erreurs_transitoires or [])
        self.appels = []

    def get(self, url, params=None, timeout=None):
        self.appels.append(url)
        if self.coupure_a is not None and len(self.appels) == self.coupure_a:
            raise KeyboardInterrupt("coupure simulée")
        if self.erreurs:
            erreur = self.erreurs.pop(0)
            if erreur == "reseau":
                raise requests.ConnectionError("réseau coupé")
            return FausseReponse(statut=erreur)
        debut = int(parse_qs(urlparse(url).query).get("after", ["0"])[0])
        page = self.lignes[debut:debut + self.taille]
        suite = debut + self.taille
        corps = {"total": len(self.lignes), "results": page}
        if suite < len(self.lignes):
            corps["next"] = f"{td.DATASET_URL}/lines?size={self.taille}&after={suite}"
        return FausseReponse(corps)


def telecharger(api, dossier):
    return td.telecharger_pages(api, "qs-test", dossier, pause=0, dormir=lambda s: None, journal=lambda m: None)


def test_pagination_suit_le_lien_next(tmp_path):
    api = FausseAPI(nb_lignes=25, taille=10)
    etat = telecharger(api, tmp_path)
    assert etat["termine"] and etat["pages"] == 3 and etat["lignes"] == 25
    assert "after" not in api.appels[0] and api.appels[1].endswith("after=10")

    sortie = tmp_path / "brut.parquet"
    assert td.assembler_pages(tmp_path, sortie) == 25
    df = pd.read_parquet(sortie)
    assert list(df.columns) == td.CHAMPS  # colonnes fixes, _score écarté
    assert df["numero_dpe"].tolist() == [f"DPE{i:04d}" for i in range(25)]


def test_reprise_apres_coupure(tmp_path):
    with pytest.raises(KeyboardInterrupt):
        telecharger(FausseAPI(nb_lignes=25, taille=10, coupure_a=3), tmp_path)
    etat = json.loads((tmp_path / "etat.json").read_text(encoding="utf-8"))
    assert etat["pages"] == 2 and not etat["termine"]

    api = FausseAPI(nb_lignes=25, taille=10)
    etat = telecharger(api, tmp_path)
    assert api.appels == [f"{td.DATASET_URL}/lines?size=10&after=20"]  # reprend à la 3e page
    assert etat["termine"] and etat["lignes"] == 25
    df = pd.read_parquet(tmp_path / "page_00003.parquet")
    assert len(df) == 5

    # Relancer une extraction terminée ne refait aucun appel
    api = FausseAPI()
    telecharger(api, tmp_path)
    assert api.appels == []


def test_reprise_refusee_si_autre_requete(tmp_path):
    telecharger(FausseAPI(nb_lignes=5), tmp_path)
    with pytest.raises(td.ErreurTelechargement):
        td.telecharger_pages(FausseAPI(), "autre-qs", tmp_path, pause=0, dormir=lambda s: None,
                             journal=lambda m: None)


def test_nouvelles_tentatives_sur_erreurs_transitoires(tmp_path):
    attentes = []
    api = FausseAPI(nb_lignes=5, erreurs_transitoires=["reseau", 503, 429])
    td.telecharger_pages(api, "qs", tmp_path, pause=0, dormir=attentes.append, journal=lambda m: None)
    assert len(api.appels) == 4
    assert attentes == [2.0, 4.0, 8.0]  # délai croissant


def test_abandon_apres_toutes_les_tentatives():
    api = FausseAPI(erreurs_transitoires=[503] * 3)
    with pytest.raises(td.ErreurTelechargement):
        td.get_avec_reessais(api, "http://x", max_tentatives=3, dormir=lambda s: None)


EXTRACTION = {"region": "93", "lignes": 1_000_000, "pages": 100, "octets_json_recus": 800_000_000,
              "octets_parquet": 100_000_000, "secondes_requetes": 300.0}


def test_estimation_metropole():
    e = td.estimer(15_000_001, EXTRACTION)
    assert e["pages_de_10000"] == 1501
    assert e["taille_json_estimee_octets"] == round(15_000_001 * 800)
    assert e["taille_parquet_estimee_octets"] == round(15_000_001 * 100)
    assert e["secondes_par_page_mesurees"] == 3.0
    assert e["duree_estimee_secondes"] == round(1501 * (3.0 + td.PAUSE_ENTRE_PAGES))
    assert e["duree_plancher_limite_debit_secondes"] == round(1501 * 60 / 600)


class FausseAPIMetropole:
    def __init__(self, ressources_datagouv):
        self.ressources = ressources_datagouv

    def get(self, url, params=None, timeout=None):
        if url.endswith("/lines"):
            return FausseReponse({"total": 300})
        if url.endswith("/values_agg"):
            return FausseReponse({"aggs": [{"value": "93", "total": 100}, {"value": "11", "total": 200},
                                           {"value": "04", "total": 7}]})
        if url.endswith("/data-files"):
            return FausseReponse([])
        if url == td.DATASET_URL:
            return FausseReponse({"isVirtual": True, "file": None, "storage": {"dataFiles": []}})
        if url == td.DATAGOUV_URL:
            return FausseReponse({"resources": self.ressources})
        raise AssertionError(url)

    def head(self, url, params=None, timeout=None, allow_redirects=True):
        return FausseReponse(statut=404)


@pytest.fixture
def dossiers(tmp_path, monkeypatch):
    monkeypatch.setattr(td, "DOSSIER_DATA", tmp_path / "data")
    monkeypatch.setattr(td, "DOSSIER_REPORTS", tmp_path / "reports")
    td.ecrire_json(tmp_path / "data" / "extraction_r93.json", EXTRACTION)
    return tmp_path


def test_metropole_sans_export(dossiers):
    lien_api = {"title": "Consultez les données", "format": "url",
                "url": "https://data.ademe.fr/datasets/dpe03existant"}
    res = td.mode_metropole(FausseAPIMetropole([lien_api]))
    assert res["total"] == 300
    assert res["par_region"] == {"93": 100, "11": 200}  # DOM (04) exclus
    assert res["exports"]["exports_complets_trouves"] == []
    assert "Aucun export complet" in res["conclusion"]
    rapport = (dossiers / "reports" / "estimation_metropole.md").read_bytes()
    assert not rapport.startswith(b"\xef\xbb\xbf")
    assert "Aucun export complet" in rapport.decode("utf-8")
    assert (dossiers / "reports" / "estimation_metropole.json").exists()


def test_metropole_avec_export(dossiers):
    export = {"title": "Export complet", "format": "parquet", "url": "https://exemple.fr/dpe.parquet"}
    res = td.mode_metropole(FausseAPIMetropole([export]))
    assert res["exports"]["exports_complets_trouves"] == ["https://exemple.fr/dpe.parquet"]
    assert "plus adapté" in res["conclusion"]


def test_metropole_exige_extraction_regionale(tmp_path, monkeypatch):
    monkeypatch.setattr(td, "DOSSIER_DATA", tmp_path)
    with pytest.raises(SystemExit):
        td.mode_metropole(FausseAPIMetropole([]))
