# EnergyHome AI — API

API FastAPI d'EnergyHome AI : prédiction de la classe DPE, assistant RAG et recommandations de travaux.
Couverture : région PACA (départements 04, 05, 06, 13, 83, 84).

## Installation

Python 3.12, dans un environnement virtuel :

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (Linux/macOS : source .venv/bin/activate)
pip install -r requirements.txt -r requirements-dev.txt
```

`scikit-learn` est figé à `1.9.0`, la version qui a créé `artifacts/modele_dpe_v2.pkl`.

Le fichier `.env` est **facultatif**. Il n'est utile que pour `/chat` et `/agent` :

```
ANTHROPIC_API_KEY=...   # génération de texte (Claude Haiku)
MISTRAL_API_KEY=...     # embeddings (mistral-embed)
```

## Lancement

```bash
uvicorn app.main:app --reload
```

Documentation interactive : http://localhost:8000/docs

## Tests

```bash
pytest
```

Les appels à Claude et Mistral sont simulés : les tests n'utilisent ni Internet ni crédits.
En CI, les tests tournent avant chaque déploiement et un échec le bloque.

## Contrat de `POST /predict`

Entrée (une erreur 422 est renvoyée si elle est invalide) :

| Champ | Valeurs |
|---|---|
| `surface` | nombre entre 9 et 1000 (m²) |
| `periode` | `avant_1948`, `1948_1974`, `1975_1977`, `1978_1982`, `1983_1988`, `1989_2000`, `2001_2005`, `2006_2012`, `2013_2021`, `apres_2021` |
| `annee_construction` | entier entre 1800 et l'année en cours, **à la place** de `periode` (exactement l'un des deux) |
| `type_batiment` | `maison`, `appartement` |
| `chauffage` | `electricite`, `electricite_renouvelable`, `gaz_naturel`, `fioul`, `gpl`, `propane`, `bois_buches`, `bois_granules`, `bois_plaquettes`, `reseau_chaleur` |
| `code_postal` | 5 chiffres, département 04, 05, 06, 13, 83 ou 84 |

```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"surface": 80, "annee_construction": 1998, "type_batiment": "maison", "chauffage": "gaz_naturel", "code_postal": "13001"}'
```

Sortie :

```json
{
  "classe": "C",
  "probabilites": {"A": 0.046, "B": 0.110, "C": 0.469, "D": 0.170, "E": 0.106, "F": 0.055, "G": 0.044},
  "model_version": "v2-rf-2025",
  "entree": {"surface": 80.0, "periode": "1989_2000", "type_batiment": "maison", "chauffage": "gaz_naturel",
             "code_postal": "13001", "departement": "13", "zone_climatique": "H3", "annee_construction": 1998}
}
```

## Structure

```
app/          code de l'API (main, core/config, api/, schemas/, ml/, rag/, agent/, db/)
training/     scripts de collecte des données et d'entraînement (à lancer depuis la racine)
artifacts/    modèle, colonnes, zones climatiques, cache des embeddings
tests/        tests pytest
```
