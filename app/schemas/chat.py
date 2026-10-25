from pydantic import BaseModel


class ChatInput(BaseModel):
    question: str
    locale: str = "fr"
