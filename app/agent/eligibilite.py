"""Éligibilité calculée à partir de l'année de construction et de la classe DPE.

Ces règles ne sont pas laissées au modèle : il les reçoit comme des faits, puis la réponse est
corrigée en code (voir app/agent/recommendations.py). Sources, vérifiées le 2026-11-04 :
- MaPrimeRénov' : logement construit depuis au moins 15 ans ; 2 ans pour une PAC air-eau,
  géothermique ou solarothermique et pour un raccordement à un réseau de chaleur (parcours par geste
  seulement) ; rénovation d'ampleur : classes E, F ou G et 15 ans sans exception (service-public F35083).
- Location : G interdit depuis 2025, F à partir de 2028, E à partir de 2034 (ecologie.gouv.fr).
"""
from dataclasses import dataclass, field
from datetime import date

GESTES_DES_2_ANS = "pompe à chaleur air-eau ou géothermique, raccordement à un réseau de chaleur"
VERIFIER = "à vérifier sur Mes Aides Réno (mesaides.france-renov.gouv.fr)"


@dataclass
class Eligibilite:
    age: int
    classe: str
    mpr_geste: str          # "oui", "limite" (gestes ouverts dès 2 ans), "a_verifier", "non"
    mpr_ampleur: str        # "oui", "a_verifier", "non"
    location: str
    gain_faible: bool
    faits: list[str] = field(default_factory=list)

    @property
    def mpr_complete(self):
        return self.mpr_geste == "oui"


def calculer(classe_dpe, annee_construction, annee=None):
    annee = date.today().year if annee is None else annee
    classe = str(classe_dpe).strip().upper()
    age = annee - int(annee_construction)
    faits = [f"Logement construit en {annee_construction}, soit environ {age} ans en {annee}."]

    # Parcours par geste. L'âge est compté en années civiles : à 15 ans (ou 2 ans) pile,
    # tout dépend de la date d'achèvement, d'où « à vérifier ».
    if age > 15:
        geste = "oui"
        faits.append("MaPrimeRénov' par geste : condition d'ancienneté remplie (15 ans) ; "
                     f"montant selon les revenus, {VERIFIER}.")
    elif age == 15:
        geste = "a_verifier"
        faits.append("MaPrimeRénov' par geste : le logement a environ 15 ans, l'éligibilité dépend de la "
                     f"date d'achèvement, {VERIFIER}.")
    elif age > 2:
        geste = "limite"
        faits.append(f"MaPrimeRénov' par geste : logement de moins de 15 ans, seuls ces gestes sont ouverts "
                     f"(dès 2 ans) : {GESTES_DES_2_ANS}. Tous les autres gestes sont non éligibles ; {VERIFIER}.")
    elif age == 2:
        geste = "a_verifier"
        faits.append("MaPrimeRénov' par geste : le logement a environ 2 ans, l'éligibilité dépend de la "
                     f"date d'achèvement, {VERIFIER}.")
    else:
        geste = "non"
        faits.append(f"MaPrimeRénov' : logement de moins de 2 ans, non éligible ; {VERIFIER}.")

    # Rénovation d'ampleur : E, F ou G et 15 ans, sans exception
    if classe not in ("E", "F", "G"):
        ampleur = "non"
        faits.append(f"MaPrimeRénov' rénovation d'ampleur : non éligible, elle est réservée aux logements "
                     f"classés E, F ou G (ce logement est classé {classe}).")
    elif age < 15:
        ampleur = "non"
        faits.append("MaPrimeRénov' rénovation d'ampleur : non éligible, le logement a moins de 15 ans.")
    elif age == 15:
        ampleur = "a_verifier"
        faits.append(f"MaPrimeRénov' rénovation d'ampleur : classe {classe} compatible, ancienneté à vérifier "
                     f"(environ 15 ans) ; {VERIFIER}.")
    else:
        ampleur = "oui"
        faits.append(f"MaPrimeRénov' rénovation d'ampleur : possible (classe {classe}, plus de 15 ans), avec un "
                     "gain d'au moins 2 classes et un Accompagnateur Rénov' obligatoire.")

    # Location (loi Climat)
    location = {
        "G": "Location : interdite depuis le 1er janvier 2025 (classe G).",
        "F": "Location : autorisée aujourd'hui, interdite à partir du 1er janvier 2028 (classe F).",
        "E": "Location : autorisée aujourd'hui, interdite à partir du 1er janvier 2034 (classe E).",
    }.get(classe, f"Location : aucune interdiction liée au DPE prévue au calendrier pour la classe {classe}.")
    faits.append(location)

    gain_faible = classe in ("A", "B")
    if gain_faible:
        faits.append(f"Classe {classe} : logement déjà performant, le gain attendu de travaux est faible ; "
                     "ne présente aucun travail comme prioritaire.")

    return Eligibilite(age=age, classe=classe, mpr_geste=geste, mpr_ampleur=ampleur,
                       location=location, gain_faible=gain_faible, faits=faits)


def item_maprimerenov(e: Eligibilite, locale="fr"):
    """Ligne d'aide imposée (remplace tout ce que le modèle a écrit sur MaPrimeRénov')."""
    if locale == "en":
        textes = {
            "oui": "MaPrimeRénov': eligible by age (15 years or more); amount depends on income, "
                   "check on Mes Aides Réno (mesaides.france-renov.gouv.fr).",
            "limite": "MaPrimeRénov': home under 15 years old, only an air-to-water or geothermal heat pump "
                      "or a heat network connection may be eligible; check on Mes Aides Réno "
                      "(mesaides.france-renov.gouv.fr).",
            "a_verifier": "MaPrimeRénov': eligibility depends on the completion date of the home; check on "
                          "Mes Aides Réno (mesaides.france-renov.gouv.fr).",
            "non": "MaPrimeRénov': not eligible (home under 2 years old).",
        }
    else:
        textes = {
            "oui": "MaPrimeRénov' : ancienneté de 15 ans remplie ; montant selon vos revenus, "
                   f"{VERIFIER}.",
            "limite": "MaPrimeRénov' : logement de moins de 15 ans, seuls une pompe à chaleur air-eau ou "
                      "géothermique ou un raccordement à un réseau de chaleur peuvent être éligibles au "
                      f"parcours par geste ; {VERIFIER}.",
            "a_verifier": f"MaPrimeRénov' : éligibilité selon la date d'achèvement du logement, {VERIFIER}.",
            "non": "MaPrimeRénov' : non éligible (logement de moins de 2 ans).",
        }
    lignes = [textes[e.mpr_geste]]
    if e.mpr_ampleur == "oui":
        lignes.append("MaPrimeRénov' rénovation d'ampleur : possible si les travaux font gagner au moins "
                      "2 classes, avec un Accompagnateur Rénov' obligatoire."
                      if locale != "en" else
                      "MaPrimeRénov' major renovation: possible if the work gains at least 2 classes, "
                      "with a mandatory Accompagnateur Rénov'.")
    return lignes
