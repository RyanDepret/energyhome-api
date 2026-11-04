# ── BASE DE CONNAISSANCES DE L'ASSISTANT (/chat et /agent) ───────────────────
# Règles en vigueur au 4 novembre 2026, vérifiées sur des sources officielles (détail et
# points non confirmés : reports/documents_rag_2026-11.md).
# Principes : un document = un sujet ; chaque chiffre provient de la source citée à la fin ;
# les montants d'aide qui changent souvent ne sont pas recopiés (renvoi au simulateur).
# Toute modification de cette liste invalide le cache des embeddings (recalcul automatique) :
# régénérer artifacts/embeddings_documents.pkl et le commiter.

from app.rag.garde_fous import RENVOI as _RENVOIS

VERIFIE_LE = "2026-11-04"

# Même phrase que celle imposée aux modèles et ajoutée par le garde-fou
RENVOI = _RENVOIS["fr"]

SP = "https://www.service-public.gouv.fr/particuliers/vosdroits/"
MPR = SP + "F35083"
CEE = SP + "F35584"
ECO_PTZ = SP + "F19905"
DPE = SP + "F16096"
AUDIT = SP + "F37110"
COPRO = SP + "F37827"
LOCATION = "https://www.ecologie.gouv.fr/politiques-publiques/interdiction-location-gel-loyers-passoires-energetiques"
ARRETE_SEUILS_DPE = "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000043353335"
ARRETE_COEF_2027 = "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000054747079"
ARRETE_S21 = "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000054190669"
TVA_PV = "https://entreprendre.service-public.gouv.fr/vosdroits/F23568"
DECLARATION_PREALABLE = SP + "F17578"


def _source(*urls):
    return f"Source : {' ; '.join(urls)} (vérifié le {VERIFIE_LE})."


documents = [
    # 1. MaPrimeRénov' : principe général
    "MaPrimeRénov' est l'aide de l'État à la rénovation énergétique, gérée par l'Anah. "
    "Elle s'adresse aux propriétaires occupants et bailleurs d'une résidence principale construite "
    "depuis au moins 15 ans (2 ans pour certains équipements du parcours par geste). Elle comporte deux parcours : le parcours par geste, "
    "pour un équipement précis, et la rénovation d'ampleur, pour un ensemble de travaux. "
    "Le montant dépend des revenus du foyer, répartis en quatre catégories (bleu, jaune, violet, rose), "
    f"et des travaux réalisés. {RENVOI}\n" + _source(MPR),

    # 2. MaPrimeRénov' par geste
    "Le parcours par geste de MaPrimeRénov' finance un équipement isolé. En 2026, ses montants ne sont "
    "prévus que pour les catégories de revenus bleu, jaune et violet. En métropole, il couvre les pompes "
    "à chaleur air-eau et géothermiques, le raccordement à un réseau de chaleur, la dépose d'une cuve "
    "à fioul et l'audit énergétique hors obligation. L'isolation, les fenêtres "
    "et le bois n'y figurent pas. Le logement doit être construit depuis au moins 15 ans ; "
    "ce délai est ramené à 2 ans pour une pompe à chaleur air-eau ou géothermique et pour un raccordement "
    f"à un réseau de chaleur. {RENVOI}\n" + _source(MPR),

    # 3. MaPrimeRénov' rénovation d'ampleur (remplace « rénovation globale »)
    "La rénovation d'ampleur de MaPrimeRénov' finance un ensemble de travaux dans un logement classé "
    "E, F ou G, construit depuis au moins 15 ans sans exception. La première étape doit faire gagner au moins 2 classes de DPE, avec au moins deux postes "
    "d'isolation. Un rendez-vous avec un conseiller France Rénov', l'accompagnement par Mon Accompagnateur "
    "Rénov' et un audit énergétique avant et après travaux sont obligatoires. L'aide est accordée avant "
    "les travaux. Taux selon les revenus : 80 % (bleu), 60 % (jaune), 45 % (violet), 10 % (rose), "
    "sur des dépenses plafonnées à 30 000 € HT (gain de 2 classes) ou 40 000 € HT (3 classes ou plus). "
    "Depuis le 1er septembre 2026, garder un chauffage au gaz en maison individuelle exclut l'aide.\n"
    + _source(MPR),

    # 4. CEE
    "Les certificats d'économies d'énergie (CEE) obligent les fournisseurs d'énergie à aider les "
    "particuliers à réduire leur consommation, sous forme de primes pour des travaux. Il n'y a pas de "
    "condition de ressources ; la prime peut être plus élevée pour les ménages modestes. L'offre du "
    "fournisseur doit être acceptée avant toute signature de devis, et les travaux réalisés par un "
    "professionnel RGE. La prime est cumulable avec MaPrimeRénov' par geste. En rénovation d'ampleur, "
    f"les CEE sont gérés par l'Anah : il ne faut pas les demander soi-même. {RENVOI}\n" + _source(CEE, MPR),

    # 5. Éco-PTZ
    "L'éco-prêt à taux zéro (éco-PTZ) finance des travaux de rénovation énergétique sans intérêts et sans "
    "condition de ressources, pour une résidence principale construite depuis plus de 2 ans. Montant "
    "maximal : 7 000 € pour une action sur les parois vitrées (fenêtres) seule, 15 000 € pour une autre "
    "action seule, 25 000 € pour deux travaux, 30 000 € pour trois travaux ou plus, et 50 000 € pour une "
    "rénovation globale. Durée de remboursement : 15 ans au plus, 20 ans pour la rénovation globale. "
    "Les travaux doivent être réalisés par une entreprise RGE. L'éco-PTZ est cumulable avec MaPrimeRénov'.\n"
    + _source(ECO_PTZ),

    # 6. Loi Climat : interdiction de louer les passoires
    "La loi Climat et résilience interdit progressivement de louer les logements les plus énergivores, "
    "jugés non décents. Calendrier par classe DPE : "
    "logement consommant plus de 450 kWh d'énergie finale par m² et par an : interdit depuis le 1er janvier 2023 ; "
    "classe G : interdit depuis le 1er janvier 2025 ; "
    "classe F : autorisé aujourd'hui, interdit à partir du 1er janvier 2028 ; "
    "classe E : autorisé aujourd'hui, interdit à partir du 1er janvier 2034. "
    "Ces interdictions s'appliquent aux nouveaux baux et aux baux renouvelés ou tacitement reconduits "
    "à partir de ces dates.\n" + _source(LOCATION),

    # 7. Gel des loyers (nouveau document)
    "Depuis le 24 août 2022, le loyer d'un logement du parc privé classé F ou G au DPE ne peut plus "
    "augmenter, pour les baux conclus, renouvelés ou tacitement reconduits après cette date. Sont "
    "interdites : la hausse entre deux locataires, la hausse au renouvellement du bail, la révision "
    "annuelle prévue par une clause d'indexation et la réévaluation du loyer dans les zones d'encadrement. "
    "La mesure concerne les locations vides, meublées et les baux mobilité, mais pas les meublés de "
    "tourisme.\n" + _source(LOCATION),

    # 8. Isolation des combles et de la toiture
    "L'isolation des combles ou de la toiture limite les pertes de chaleur par le haut du logement. "
    "En 2026, elle ne figure pas dans la liste des travaux du parcours par geste de MaPrimeRénov' en "
    "métropole ; la toiture est en revanche l'un des postes de travaux de la rénovation d'ampleur. "
    "Elle peut être aidée par une prime CEE, à demander avant la signature du devis, et financée par "
    "l'éco-PTZ. Pour ouvrir droit à ces aides, les travaux doivent être réalisés par un professionnel "
    f"RGE. {RENVOI}\n" + _source(MPR, CEE),

    # 9. Pompe à chaleur air-eau
    "Une pompe à chaleur (PAC) air-eau prélève la chaleur de l'air extérieur pour chauffer le logement "
    "et l'eau chaude. Elle fonctionne à l'électricité, ce qui compte dans le calcul du DPE. En 2026, "
    "elle fait partie des travaux du parcours par geste de MaPrimeRénov' pour les catégories de revenus "
    "bleu, jaune et violet, et peut aussi recevoir une prime CEE demandée avant la signature du devis. "
    "Dans une rénovation d'ampleur, les PAC hybrides gaz ou fioul ne sont plus finançables. La PAC "
    "air-air, elle, ne figure pas dans le parcours par geste. "
    f"L'installateur doit être RGE. {RENVOI}\n" + _source(MPR, CEE),

    # 10. DPE : classes, seuils, validité
    "Le diagnostic de performance énergétique (DPE) classe un logement de A à G selon deux critères : "
    "la consommation d'énergie primaire et les émissions de gaz à effet de serre. La classe retenue est "
    "la plus mauvaise des deux. Seuils supérieurs (kWh/m²/an et kg CO2/m²/an) : A 70 et 6, B 110 et 11, "
    "C 180 et 30, D 250 et 50, E 330 et 70, F 420 et 100 ; au-delà, classe G. Les seuils sont adaptés pour "
    "les logements de 40 m² ou moins et, pour E et F, au-dessus de 800 m d'altitude. Le DPE est obligatoire "
    "pour vendre ou louer et valable 10 ans ; ceux réalisés avant le 1er juillet 2021 ne sont plus "
    "valables.\n" + _source(ARRETE_SEUILS_DPE, DPE),

    # 11. DPE : coefficient de l'électricité (nouveau document)
    "Dans le DPE, la consommation d'électricité est convertie en énergie primaire par un coefficient. "
    "Il est passé de 2,3 à 1,9 le 1er janvier 2026 et passera à 1,7 le 1er janvier 2027 (arrêté du "
    "19 août 2026). L'étiquette des logements chauffés à l'électricité, pompe à chaleur comprise, peut "
    "donc s'améliorer sans travaux. Un DPE réalisé en 2025 ou avant reste valable ; si son étiquette "
    "s'améliore, il peut être mis à jour gratuitement, sans nouvelle visite du diagnostiqueur, en "
    "téléchargeant une attestation sur le service officiel « Vérifier son DPE ou audit énergétique ».\n"
    + _source(DPE, ARRETE_COEF_2027),

    # 12. Isolation des murs par l'extérieur
    "L'isolation des murs par l'extérieur (ITE) consiste à poser un isolant sur les façades. Elle limite "
    "les ponts thermiques et ne réduit pas la surface habitable. En 2026, l'isolation des murs ne figure "
    "pas dans le parcours par geste de MaPrimeRénov' en métropole. Elle reste finançable dans une "
    "rénovation d'ampleur, dont les murs sont l'un des postes de travaux, par une prime CEE demandée avant "
    "la signature du devis, et par l'éco-PTZ. Le gain de classe DPE dépend du logement et des autres "
    f"travaux réalisés. {RENVOI}\n" + _source(MPR, CEE, ECO_PTZ),

    # 13. Fenêtres
    "Remplacer des fenêtres à simple vitrage par du double ou du triple vitrage réduit les pertes de "
    "chaleur et l'effet de paroi froide. En 2026, les fenêtres ne figurent pas dans le parcours par geste "
    "de MaPrimeRénov' en métropole ; les menuiseries restent l'un des postes de la rénovation d'ampleur. "
    "L'éco-PTZ finance jusqu'à 7 000 € pour une action sur les parois vitrées seule. Une prime CEE peut "
    "aussi être demandée à un fournisseur d'énergie, avant la signature du devis, pour des travaux "
    f"réalisés par un professionnel RGE. {RENVOI}\n" + _source(MPR, ECO_PTZ, CEE),

    # 14. VMC
    "La ventilation mécanique contrôlée (VMC) renouvelle l'air du logement et évite les problèmes "
    "d'humidité, ce qui devient indispensable après des travaux d'isolation. Une VMC double flux récupère "
    "une partie de la chaleur de l'air extrait. En 2026, la ventilation est l'un des postes de travaux de "
    "la rénovation d'ampleur de MaPrimeRénov' ; elle ne figure pas dans la liste du parcours par geste "
    "en métropole. Une prime CEE peut être demandée avant la signature du devis, pour des travaux réalisés "
    f"par un professionnel RGE. {RENVOI}\n" + _source(MPR, CEE),

    # 15. Chauffe-eau thermodynamique
    "Le chauffe-eau thermodynamique produit l'eau chaude sanitaire grâce à une pompe à chaleur qui capte "
    "les calories de l'air ; il fonctionne à l'électricité. En 2026, il ne figure pas dans la liste des "
    "travaux du parcours par geste de MaPrimeRénov' en métropole ; l'eau chaude est en revanche l'un des "
    "postes possibles d'une rénovation d'ampleur. Une prime CEE peut être demandée à un fournisseur "
    "d'énergie avant la signature du devis, et l'installateur doit être RGE. "
    f"{RENVOI}\n" + _source(MPR, CEE),

    # 16. Photovoltaïque
    "Des panneaux photovoltaïques produisent de l'électricité consommée sur place (autoconsommation) ; "
    "le surplus peut être vendu. Pour une installation sur bâtiment de 9 kWc ou moins, seule la vente du "
    "surplus est possible : la vente totale n'est plus éligible. L'arrêté du 1er juin 2026 fixe le tarif d'achat du surplus "
    "par l'acheteur obligé (EDF OA) à 1,1 c€/kWh hors TVA, pour un contrat de 20 ans indexé de 2 % par an, "
    "et ne prévoit plus de prime à l'autoconsommation. Une installation se justifie donc par l'électricité "
    "consommée sur place, pas par la revente. La TVA est de 5,5 % jusqu'à 9 kW, sous conditions.\n"
    + _source(ARRETE_S21, TVA_PV),

    # 17. Audit énergétique
    "L'audit énergétique est obligatoire pour vendre une maison individuelle ou un immeuble de logements "
    "appartenant à un seul propriétaire, classé E, F ou G au DPE. L'obligation existe depuis le "
    "1er avril 2023 et sera étendue à la classe D le 1er janvier 2034. Valable 5 ans, l'audit propose des "
    "scénarios de travaux pour améliorer la classe du logement. Il est réalisé par un professionnel "
    "qualifié, notamment un architecte ou un professionnel RGE, sans sous-traitance ; son prix est libre. "
    "Un audit avant et après travaux est aussi exigé pour la rénovation d'ampleur de MaPrimeRénov'.\n"
    + _source(AUDIT, MPR),

    # 18. Label RGE
    "Le label RGE (Reconnu garant de l'environnement) atteste la qualification d'une entreprise pour des "
    "travaux d'économies d'énergie. Il est exigé pour obtenir MaPrimeRénov', les primes CEE et l'éco-PTZ. "
    "Avant de signer un devis, vérifiez que l'entreprise est RGE pour le type de travaux prévu. "
    "L'annuaire officiel de France Rénov' permet de trouver un professionnel RGE par code postal. "
    "Il est conseillé de demander au moins 3 devis pour comparer les offres et les solutions techniques "
    "proposées.\n" + _source(CEE, ECO_PTZ, MPR),

    # 19. France Rénov' et Mon Accompagnateur Rénov'
    "France Rénov' est le service public de la rénovation de l'habitat : ses conseillers informent "
    "gratuitement sur les travaux et les aides, au 0 808 800 700 du lundi au vendredi. Mon Accompagnateur "
    "Rénov' est un rôle distinct : un professionnel qui accompagne le ménage tout au long d'un projet de "
    "rénovation. Il est obligatoire pour la rénovation d'ampleur de MaPrimeRénov', après un rendez-vous "
    "avec un conseiller France Rénov'. Son coût est payant mais pris en charge selon les revenus du foyer, "
    "de 100 % à 20 %, dans une limite fixée par l'Anah.\n" + _source(MPR),

    # 20. Copropriété
    "En copropriété, les travaux sur les parties communes sont décidés en assemblée générale. "
    "MaPrimeRénov' Copropriété est demandée par le syndic au nom du syndicat des copropriétaires. "
    "Les travaux doivent améliorer la performance énergétique d'au moins 35 %. L'aide couvre 30 % des "
    "travaux pour un gain d'au moins 35 %, et 45 % pour un gain d'au moins 50 %, dans la limite de "
    "25 000 € de travaux par logement. Un assistant à maîtrise d'ouvrage est obligatoire. Le recours à "
    "l'aide et les travaux sont votés à la majorité absolue ; avec au moins un tiers des voix, un second "
    "vote à la majorité simple est possible.\n" + _source(COPRO),

    # 21. Déclaration préalable de travaux (nouveau)
    "Des travaux de rénovation énergétique qui modifient l'aspect extérieur d'une maison peuvent exiger "
    "une déclaration préalable de travaux en mairie, y compris hors copropriété : isolation thermique "
    "par l'extérieur, ravalement de façade, panneau solaire sur le toit, remplacement de fenêtres ou de "
    "fenêtres de toit qui change l'aspect extérieur. Une fois le dossier complet, le délai d'instruction "
    "est en général d'un mois, et de deux mois en secteur protégé (abords d'un monument historique, site "
    "patrimonial remarquable, site classé ou inscrit). Les règles locales d'urbanisme se vérifient auprès "
    "de la mairie. En copropriété, le vote de l'assemblée générale s'ajoute pour les parties communes.\n"
    + _source(DECLARATION_PREALABLE, COPRO),

    # 22. TVA des travaux de rénovation énergétique (nouveau)
    "La TVA à 5,5 % ne concerne pas tous les travaux. En métropole, elle s'applique aux travaux "
    "d'amélioration de la qualité énergétique d'un logement achevé depuis au moins 2 ans : isolation "
    "thermique (parois, fenêtres, portes d'entrée, volets isolants), équipements de chauffage et d'eau "
    "chaude utilisant une énergie renouvelable, ventilation mécanique contrôlée, régulation du chauffage, "
    "et panneaux solaires jusqu'à 9 kW sous conditions. D'autres travaux d'amélioration ou d'entretien "
    "relèvent du taux de 10 %. Les systèmes de climatisation, les équipements ménagers et le mobilier ne "
    "bénéficient pas du taux réduit. Les travaux doivent respecter les exigences techniques du Code général "
    "des impôts.\n" + _source(TVA_PV),
]

# Documents joints d'office par /agent, retrouvés par leur début (et non par leur position)
DEBUTS = {
    "mpr": "MaPrimeRénov' est l'aide",
    "mpr_geste": "Le parcours par geste",
    "mpr_ampleur": "La rénovation d'ampleur",
    "location": "La loi Climat",
    "coefficient": "Dans le DPE, la consommation d'électricité",
    "accompagnateur": "France Rénov' est le service public",
    "declaration": "Des travaux de rénovation énergétique qui modifient",
    "tva": "La TVA à 5,5 %",
}


def indice(sujet):
    """Position du document d'un sujet de DEBUTS (ValueError si aucun document ne commence ainsi)."""
    debut = DEBUTS[sujet]
    for i, doc in enumerate(documents):
        if doc.startswith(debut):
            return i
    raise ValueError(f"Aucun document ne commence par {debut!r}")
