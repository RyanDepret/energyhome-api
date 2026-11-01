"""Erreurs typées des services externes (Claude, Mistral), converties en 503 par l'API."""


class ServiceIndisponible(RuntimeError):
    """Un service externe ne répond pas correctement : l'API renvoie 503 avec `message_public`.

    `str(exception)` garde le détail technique (journaux, tests) ; seul `message_public` est envoyé au client.
    """

    code = "service_indisponible"

    def __init__(self, message_public: str, detail_technique: str = ""):
        super().__init__(f"{message_public} ({detail_technique})" if detail_technique else message_public)
        self.message_public = message_public


class ModeleIndisponible(ServiceIndisponible):
    """Le modèle de génération (Claude ou Mistral) est saturé, injoignable ou sans clé API."""

    code = "modele_indisponible"

    def __init__(self, modele: str, raison: str, detail_technique: str = ""):
        nom = {"claude": "Claude", "mistral": "Mistral"}.get(modele, modele)
        super().__init__(f"{nom} est momentanément indisponible ({raison}), réessayez dans un instant.",
                         detail_technique)
        self.modele = modele


class RechercheIndisponible(ServiceIndisponible):
    """La recherche documentaire (embedding de la question par Mistral) a échoué."""

    code = "recherche_indisponible"

    def __init__(self, raison: str, detail_technique: str = ""):
        super().__init__(f"Recherche documentaire momentanément indisponible ({raison}), réessayez dans un instant.",
                         detail_technique)
