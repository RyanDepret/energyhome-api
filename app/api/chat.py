from fastapi import APIRouter

from app.rag.query import rag_query
from app.schemas.chat import ChatInput

router = APIRouter()


@router.post("/chat")
def chat_assistant(data: ChatInput):
    return rag_query(data.question, locale=data.locale)
