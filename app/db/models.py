from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.db.database import Base


# ── CONTACT ───────────────────────────────────────────────────────────────────

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100))
    email = Column(String(150))
    message = Column(Text)
    # Date d'envoi enregistrée automatiquement
    date_envoi = Column(DateTime, default=func.now())
