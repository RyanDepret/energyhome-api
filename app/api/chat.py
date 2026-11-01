from fastapi import APIRouter

from app.rag.query import rag_query
from app.schemas.chat import ChatInput, ChatOutput

router = APIRouter()


@router.post("/chat", response_model=ChatOutput, response_model_exclude_none=True)
def chat_assistant(data: ChatInput):
    return rag_query(data.question, locale=data.locale, modele=data.modele)
