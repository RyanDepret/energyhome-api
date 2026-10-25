from fastapi import APIRouter

from app.core.config import settings
from app.ml import model
from app.ml.features import annee_vers_periode, build_features
from app.schemas.predict import PredictionInput, PredictionOutput

router = APIRouter()


@router.post("/predict", response_model=PredictionOutput)
def predict_dpe(data: PredictionInput):
    """Prédit la classe DPE d'un logement via le modèle Random Forest v2."""
    periode = data.periode or annee_vers_periode(data.annee_construction)
    departement = data.code_postal[:2]
    zone = model.zone_climatique(departement)

    features = build_features(
        surface=data.surface,
        periode=periode,
        type_batiment=data.type_batiment,
        chauffage=data.chauffage,
        zone_climatique=zone,
        colonnes_modele=model.get_columns(),
    )
    classe, probabilites = model.predict(features)

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
        model_version=settings.model_version,
        entree=entree,
    )
