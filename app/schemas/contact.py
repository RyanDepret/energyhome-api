from pydantic import BaseModel


class ContactInput(BaseModel):
    nom: str
    email: str
    message: str
