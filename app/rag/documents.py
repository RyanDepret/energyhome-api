# ── BASE DE CONNAISSANCES ─────────────────────────────────────────────────────

documents = [
    """MaPrimeRénov' est une aide de l'État français pour financer les travaux 
    de rénovation énergétique. Elle est accessible à tous les propriétaires, 
    occupants ou bailleurs. Le montant varie selon les revenus du foyer et le 
    type de travaux. Pour un logement classé F ou G, les aides peuvent atteindre 
    jusqu'à 70 000 euros pour une rénovation globale.""",

    """Les Certificats d'Économies d'Énergie (CEE) obligent les fournisseurs 
    d'énergie à financer des travaux de rénovation chez les particuliers. 
    Cette aide est cumulable avec MaPrimeRénov'. Le montant dépend des économies 
    d'énergie générées par les travaux réalisés.""",

    """L'éco-prêt à taux zéro (éco-PTZ) permet d'emprunter jusqu'à 50 000 euros 
    sans payer d'intérêts pour financer des travaux de rénovation énergétique. 
    Il est accessible sans condition de ressources et remboursable sur 20 ans maximum.""",

    """La loi Climat et Résilience interdit progressivement la location des 
    passoires thermiques. Depuis le 1er janvier 2025, les logements classés G 
    sont interdits à la location. Les logements F le seront au 1er janvier 2028, 
    et les logements E au 1er janvier 2034.""",

    """L'isolation des combles est le travail le plus rentable en rénovation 
    énergétique. Elle permet de réduire jusqu'à 30% des déperditions de chaleur. 
    Le coût moyen est de 20 à 50 euros par m² et le retour sur investissement 
    est généralement inférieur à 5 ans.""",

    """Une pompe à chaleur air-eau permet de réduire la facture de chauffage 
    de 50 à 70%. Le coût d'installation varie entre 10 000 et 18 000 euros. 
    Avec MaPrimeRénov' et les CEE, le reste à charge peut descendre à 3 000 euros 
    pour les ménages modestes.""",

    """Le Diagnostic de Performance Énergétique (DPE) classe les logements 
    de A à G selon leur consommation d'énergie et leurs émissions de CO2. 
    La classe A correspond à moins de 70 kWh/m²/an, la classe B entre 70 et 110, 
    la classe C entre 110 et 180, la classe D entre 180 et 250, la classe E 
    entre 250 et 330, la classe F entre 330 et 420, et la classe G au-delà 
    de 420 kWh/m²/an. Un DPE est valable 10 ans et est obligatoire pour toute 
    vente ou location.""",

    """L'isolation des murs par l'extérieur (ITE) est la technique la plus 
    efficace pour les maisons individuelles. Elle supprime les ponts thermiques 
    et ne réduit pas la surface habitable. Le coût moyen est de 100 à 200 euros 
    par m² de façade. Elle permet de gagner 1 à 2 classes DPE et de réduire 
    la facture de chauffage de 25 à 35%.""",

    """Le remplacement des fenêtres par du double ou triple vitrage réduit 
    les déperditions thermiques de 10 à 15%. Le coût moyen est de 300 à 800 euros 
    par fenêtre selon la taille et le matériau. L'aide CEE peut couvrir jusqu'à 
    100 euros par fenêtre. C'est un travail recommandé en priorité pour les 
    logements construits avant 1990 équipés de simple vitrage.""",

    """La ventilation mécanique contrôlée (VMC) est essentielle dans un logement 
    bien isolé pour renouveler l'air et éviter les problèmes d'humidité. 
    Une VMC double flux récupère jusqu'à 90% de la chaleur de l'air extrait. 
    Le coût d'installation est de 3 000 à 8 000 euros. Elle est éligible 
    à MaPrimeRénov' et aux CEE, avec une aide pouvant atteindre 2 500 euros.""",

    """Le chauffe-eau thermodynamique (CET) utilise les calories de l'air ambiant 
    pour produire de l'eau chaude sanitaire. Il consomme 3 fois moins d'électricité 
    qu'un chauffe-eau électrique classique. Le coût est de 1 500 à 3 000 euros 
    installé. MaPrimeRénov' offre jusqu'à 1 200 euros d'aide. Le retour sur 
    investissement est de 4 à 6 ans.""",

    """Les panneaux solaires photovoltaïques permettent de produire sa propre 
    électricité et de réduire sa facture énergétique. Une installation de 3 kWc 
    coûte entre 7 000 et 9 000 euros. La prime à l'autoconsommation versée par 
    l'État atteint 380 euros par kWc installé. L'excédent d'électricité peut 
    être revendu à EDF à un tarif garanti sur 20 ans.""",

    """L'audit énergétique est un diagnostic approfondi du logement réalisé 
    par un professionnel certifié RGE. Il est obligatoire depuis 2023 pour vendre 
    un logement classé F ou G. Il coûte entre 500 et 1 000 euros mais peut être 
    financé à 70% par MaPrimeRénov'. Il propose un plan de travaux chiffré 
    et priorisé pour améliorer la classe DPE.""",

    """Le label RGE (Reconnu Garant de l'Environnement) est obligatoire pour 
    bénéficier des aides publiques à la rénovation énergétique. Il garantit 
    la compétence du professionnel dans les travaux d'efficacité énergétique. 
    Pour trouver un artisan RGE, le site France Rénov' propose un annuaire 
    gratuit par code postal. Il est conseillé de demander au moins 3 devis.""",

    """France Rénov' est le service public de la rénovation énergétique. 
    Il propose un accompagnement gratuit par des conseillers indépendants 
    appelés Mon Accompagnateur Rénov' (MAR). Cet accompagnement est obligatoire 
    pour les projets de rénovation globale financés par MaPrimeRénov' Ampleur. 
    Le MAR aide à définir le programme de travaux et choisir les artisans RGE.""",

    """La rénovation globale consiste à réaliser plusieurs travaux en une seule 
    fois pour atteindre au minimum la classe C. Elle est fortement encouragée 
    par l'État via MaPrimeRénov' Ampleur qui finance jusqu'à 70% des travaux 
    pour les ménages modestes, avec un plafond de 70 000 euros. Elle est plus 
    efficace et moins coûteuse que des travaux réalisés au fil des années.""",

    """Pour un appartement en copropriété, les travaux de rénovation énergétique 
    concernent à la fois les parties privatives et les parties communes. 
    Le syndicat de copropriété doit voter les travaux sur parties communes 
    à la majorité absolue. MaPrimeRénov' Copropriétés finance jusqu'à 45% 
    des travaux collectifs.""",
]
