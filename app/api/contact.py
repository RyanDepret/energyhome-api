from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Contact
from app.schemas.contact import ContactInput

router = APIRouter()


@router.post("/contact")
def contact(data: ContactInput, db: Session = Depends(get_db)):
    # Sauvegarde du message de contact en base de données
    message = Contact(**data.model_dump())
    db.add(message)
    db.commit()
    return {"message": "Message envoyé avec succès"}
