from fastapi import APIRouter

from app.core.config import settings
from app.ml import model, modele_v3
from app.ml.features import annee_vers_periode, build_features
from app.schemas.predict import PredictionInput, PredictionOutput

router = APIRouter()


def utilise_v2() -> bool:
    return settings.model_version.startswith("v2")


def artefact_v3() -> dict:
    """Artefacts v3 ; refuse un dossier dont la version ne correspond pas au réglage."""
    artefact = modele_v3.charger(settings.model_v3_dir)
    version = artefact["metadonnees"]["version"]
    if version != settings.model_version:
        raise RuntimeError(f"{settings.model_v3_dir} contient la version {version!r}, "
                           f"réglage MODEL_VERSION = {settings.model_version!r}")
    return artefact


@router.post("/predict", response_model=PredictionOutput)
def predict_dpe(data: PredictionInput):
    """Prédit la classe DPE d'un logement (modèle choisi par MODEL_VERSION)."""
    periode = data.periode or annee_vers_periode(data.annee_construction)
    departement = data.code_postal[:2]
    zone = model.zone_climatique(departement)

    importances = []
    if utilise_v2():
        features = build_features(
            surface=data.surface,
            periode=periode,
            type_batiment=data.type_batiment,
            chauffage=data.chauffage,
            zone_climatique=zone,
            colonnes_modele=model.get_columns(),
        )
        classe, probabilites = model.predict(features)
    else:
        entree_modele = {
            "surface": data.surface,
            "periode": periode.value,
            "type_batiment": data.type_batiment.value,
            "chauffage": data.chauffage.value,
            "departement": departement,
            "zone_climatique": zone,
        }
        classe, probabilites, importances = modele_v3.predire(artefact_v3(), entree_modele)

    # Valeurs normalisées réellement utilisées par le modèle
    entree = {
        "surface": data.surface,
        "periode": periode.value,
        "type_batiment": data.type_batiment.value,
        "chauffage": data.chauffage.value,
        "code_postal": data.code_postal,
        "departement": departement,
        "zone_climatique": zone,
    }
    if data.annee_construction is not None:
        entree["annee_construction"] = data.annee_construction

    return PredictionOutput(
        classe=classe,
        probabilites=probabilites,
        importances=importances,
        model_version=settings.model_version,
        entree=entree,
    )
