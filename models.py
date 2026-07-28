from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from database import Base


# ── LOGEMENTS ────────────────────────────────────────────────────────────────

class Logement(Base):
    __tablename__ = "logements"

    id = Column(Integer, primary_key=True, index=True)
    surface = Column(Numeric)
    annee_construction = Column(Integer)
    classe_dpe = Column(String(1))
    consommation_kwh = Column(Numeric)
    type_chauffage = Column(String(50))
    ville = Column(String(100))
    code_postal = Column(String(5))
    date_diagnostic = Column(Date)


# ── TRAVAUX ───────────────────────────────────────────────────────────────────

class Travaux(Base):
    __tablename__ = "travaux"

    id = Column(Integer, primary_key=True, index=True)
    logement_id = Column(Integer, ForeignKey("logements.id"))
    type_travaux = Column(String(100))
    cout_estime = Column(Numeric)
    gain_classe = Column(String(1))


# ── CONTACT ───────────────────────────────────────────────────────────────────

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100))
    email = Column(String(150))
    message = Column(Text)
    # Date d'envoi enregistrée automatiquement
    date_envoi = Column(DateTime, default=func.now())