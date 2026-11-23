from .relances import verifier_relances


class RelancesPaiementMiddleware:
    """Déclenche les relances de paiement au fil des visites (au plus une fois par heure, en tâche de fond)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith(('/static/', '/media/')):
            verifier_relances()
        return response
