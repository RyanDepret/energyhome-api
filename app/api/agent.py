from fastapi import APIRouter

from app.agent.recommendations import agent_recommandations
from app.schemas.agent import AgentInput

router = APIRouter()


@router.post("/agent")
def agent_dpe(data: AgentInput):
    return agent_recommandations(
        classe_dpe=data.classe_dpe,
        surface=data.surface,
        annee_construction=data.annee_construction,
        type_batiment=data.type_batiment,
        type_chauffage=data.type_chauffage,
        code_postal=data.code_postal,
        locale=data.locale
    )
