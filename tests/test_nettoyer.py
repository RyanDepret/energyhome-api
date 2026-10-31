"""Règles de nettoyage sur un petit jeu factice."""

import pandas as pd

from training import nettoyer as n

COLONNES_MODELE = [
    "surface_habitable_logement",
    "periode_construction_1948-1974",
    "type_batiment_maison",
    "type_energie_principale_chauffage_Gaz naturel",
    "zone_climatique_H3",
]


def dpe(numero, etiquette="D", surface=80.0, remplace=None, date="2025-01-01", modif=None,
        chauffage="Gaz naturel", periode="1948-1974"):
    return {
        "numero_dpe": numero,
        "numero_dpe_remplace": remplace,
        "date_etablissement_dpe": date,
        "date_derniere_modification_dpe": modif or date,
        "etiquette_dpe": etiquette,
        "surface_habitable_logement": surface,
        "periode_construction": periode,
        "type_batiment": "maison",
        "type_energie_principale_chauffage": chauffage,
        "zone_climatique": "H3",
    }


def test_dedoublonnage_par_identifiant_garde_la_version_la_plus_recente():
    df = pd.DataFrame([
        dpe("A", etiquette="E", modif="2025-01-01"),
        dpe("A", etiquette="C", modif="2025-06-01"),
        dpe("A", etiquette="F", modif="2025-03-01"),
        dpe(None),
    ])
    garde, detail = n.dedoublonner(df)
    assert garde["etiquette_dpe"].tolist() == ["C"]
    assert detail == {"sans_identifiant": 1, "doublons_identifiant": 2}


def test_lignes_identiques_mais_identifiants_differents_conservees():
    df = pd.DataFrame([dpe("A"), dpe("B")])  # mêmes caractéristiques, deux logements réels
    garde, detail = n.dedoublonner(df)
    assert len(garde) == 2 and detail["doublons_identifiant"] == 0


def test_dpe_remplace_seul_le_plus_recent_reste():
    df = pd.DataFrame([
        dpe("A", date="2024-01-01"),
        dpe("B", remplace="A", date="2024-06-01"),
        dpe("C", remplace="B", date="2025-01-01"),   # chaîne A → B → C
        dpe("D", remplace="ABSENT", date="2025-01-01"),  # remplace un DPE hors du jeu : conservé
        dpe("E", date="2025-05-01"),
        dpe("F", remplace="E", date="2025-02-01"),   # le remplacé est plus récent : on garde E
    ])
    garde, detail = n.retirer_remplaces(df)
    assert sorted(garde["numero_dpe"]) == ["C", "D", "E"]
    assert detail == {"avec_numero_dpe_remplace": 4, "paires_presentes": 3, "remplace_plus_recent_que_remplacant": 1, "lignes_retirees": 3}


def test_etiquette_manquante_ou_hors_A_G():
    df = pd.DataFrame([dpe("A", "A"), dpe("B", "G"), dpe("C", None), dpe("D", "H"), dpe("E", "c")])
    garde, detail = n.filtrer_etiquette(df)
    assert garde["numero_dpe"].tolist() == ["A", "B"]
    assert detail["manquante"] == 1 and detail["hors_A_G"] == 2


def test_surface_absente_ou_aberrante():
    df = pd.DataFrame([dpe("A", surface=9), dpe("B", surface=1000), dpe("C", surface=8.9),
                       dpe("D", surface=1000.5), dpe("E", surface=None)])
    garde, detail = n.filtrer_surface(df)
    assert garde["numero_dpe"].tolist() == ["A", "B"]
    assert detail == {"absente": 1, "inferieure_a_9": 1, "superieure_a_1000": 1}


def test_categories_inconnues_comptees_sans_suppression():
    df = pd.DataFrame([dpe("A"), dpe("B", chauffage="Charbon"), dpe("C", chauffage="Charbon"),
                       dpe("D", periode=None)])
    propre, bilan = n.nettoyer(df, COLONNES_MODELE)
    assert len(propre) == 4  # rien supprimé
    inconnues = bilan["categories_inconnues_du_modele"]
    assert inconnues["type_energie_principale_chauffage"] == {"Charbon": 2}
    assert inconnues["periode_construction"] == {"(manquant)": 1}
    assert inconnues["zone_climatique"] == {}


def test_bilan_complet_et_repartition():
    df = pd.DataFrame([dpe("A", "A"), dpe("A", "A"), dpe("B", "C"), dpe("C", None), dpe("D", "C", surface=5)])
    propre, bilan = n.nettoyer(df, COLONNES_MODELE)
    assert [(e["avant"], e["apres"]) for e in bilan["etapes"]] == [(5, 4), (4, 4), (4, 3), (3, 2)]
    assert bilan["repartition"]["A"] == {"effectif": 1, "pourcentage": 50.0}
    assert bilan["repartition"]["G"]["effectif"] == 0
