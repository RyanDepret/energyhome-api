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
MISTRAL_API_KEY=...     # embeddings (mistral-embed) et génération avec modele=mistral
```

Réglages facultatifs : `MISTRAL_CHAT_MODEL` (défaut `mistral-small-latest`), `GENERATION_TIMEOUT_S` (défaut 30),
`EMBEDDING_TIMEOUT_S` (défaut 10).

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

Sortie (modèle v3) :

```json
{
  "classe": "C",
  "probabilites": {"A": 0.0, "B": 0.005, "C": 0.905, "D": 0.085, "E": 0.004, "F": 0.0, "G": 0.0},
  "importances": [
    {"critere": "Période de construction", "valeur": "1989_2000", "poids": 0.548},
    {"critere": "Énergie de chauffage", "valeur": "gaz_naturel", "poids": 0.226},
    {"critere": "Département", "valeur": "13", "poids": 0.121},
    {"critere": "Type de bâtiment", "valeur": "maison", "poids": 0.098},
    {"critere": "Surface", "valeur": 80.0, "poids": 0.006}
  ],
  "model_version": "v3-lightgbm-2026-11",
  "entree": {"surface": 80.0, "periode": "1989_2000", "type_batiment": "maison", "chauffage": "gaz_naturel",
             "code_postal": "13001", "departement": "13", "zone_climatique": "H3", "annee_construction": 1998}
}
```

`probabilites` sont calibrées ; `importances` donne le poids de chaque critère dans la prédiction
(contributions SHAP, somme des poids = 1). Le modèle servi se choisit par la variable d'environnement
`MODEL_VERSION` : `v3-lightgbm-2026-11` par défaut (artefacts dans `artifacts/v3/`), `v2-rf-2025` pour revenir
à l'ancien modèle (`importances` est alors vide). Fiche du modèle : `reports/fiche_modele_v3.md`.

## Contrat de `POST /chat`

Assistant documentaire : la question est comparée à la base de connaissances (embeddings `mistral-embed`),
les 3 passages les plus proches servent de contexte, puis un modèle rédige la réponse.

Entrée (422 si invalide) :

| Champ | Valeurs |
|---|---|
| `question` | texte |
| `locale` | `fr` (défaut) ou `en` : langue de la réponse |
| `modele` | `claude` (défaut, Claude Haiku 4.5) ou `mistral` (`mistral-small-latest`) ; toute autre valeur : 422 |

Les deux modèles reçoivent **exactement le même prompt**, construit à partir des **mêmes passages** :
`sources` est identique quel que soit `modele`, seule la génération change. Même plafond de 1000 tokens.

Sortie (réponse réelle du 2026-11-01, `reponse` abrégée) :

```json
{
  "question": "Quelles aides pour installer une pompe à chaleur ?",
  "reponse": "Pour une pompe à chaleur air-eau, vous pouvez bénéficier de : MaPrimeRénov' ... CEE ...",
  "sources": [
    {"extrait": "Une pompe à chaleur air-eau permet de réduire la facture de chauffage ...", "score": 0.857},
    {"extrait": "Le chauffe-eau thermodynamique (CET) utilise les calories de l'air ambiant ...", "score": 0.8251},
    {"extrait": "MaPrimeRénov' est une aide de l'État français pour financer les travaux ...", "score": 0.8007}
  ],
  "modele": "mistral",
  "duree_ms": 2909,
  "tokens": {"entree": 396, "sortie": 134}
}
```

- `duree_ms` : temps de génération seul (hors recherche documentaire), nouvelles tentatives comprises.
- `tokens` : présent seulement si le fournisseur renvoie l'usage (c'est le cas de Claude et de Mistral aujourd'hui).

Erreurs (toutes portent l'en-tête CORS, pour que le navigateur affiche le message) :

| Statut | `code` | Cas |
|---|---|---|
| 503 | `modele_indisponible` | modèle saturé (429/5xx après 2 nouvelles tentatives), délai dépassé, clé absente |
| 503 | `recherche_indisponible` | embedding de la question en échec (délai dépassé, erreur Mistral, clé absente) |
| 500 | `erreur_interne` | erreur inattendue |

```json
{"detail": "Mistral est momentanément indisponible (service saturé), réessayez dans un instant.", "code": "modele_indisponible"}
```

Robustesse : chaque appel externe a un délai maximal (génération 30 s, embedding 10 s). Mistral (génération) :
1 appel + 2 nouvelles tentatives sur 429 et 5xx, après 1 s puis 2 s ; Claude : même nombre de tentatives,
gérées par le SDK Anthropic. L'embedding n'est pas retenté : en cas d'échec, 503 immédiat.
`mistral-small-latest` a été vérifié dans `GET /v1/models` le 2026-11-01 (alias de `mistral-small-2603`).
`/agent` utilise la même génération Claude : il renvoie lui aussi 503 quand Claude ou la recherche est indisponible.

## Structure

```
app/          code de l'API (main, core/config, api/, schemas/, ml/, rag/, agent/, db/)
training/     scripts de collecte des données et d'entraînement (à lancer depuis la racine)
artifacts/    modèle, colonnes, zones climatiques, cache des embeddings
tests/        tests pytest
```
