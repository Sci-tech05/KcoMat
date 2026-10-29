from .rappels import verifier_rappels


class RappelsWebinairesMiddleware:
    """Déclenche les rappels « 20 min avant » au fil des visites (complète la tâche planifiée éventuelle)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith(('/static/', '/media/')):
            verifier_rappels()
        return response
