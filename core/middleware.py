from django.conf import settings

from .relances import verifier_relances


class ContentSecurityPolicyMiddleware:
    """En-tête Content-Security-Policy construit depuis settings.CSP_DIRECTIVES.

    Une vue peut autoriser des origines supplémentaires pour une seule page (salle Jitsi
    hébergée sur un autre domaine) avec ``response.csp_origines = ['https://meet.exemple']`` :
    elles sont ajoutées à script-src et frame-src.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        entete = 'Content-Security-Policy-Report-Only' if settings.CSP_REPORT_ONLY else 'Content-Security-Policy'
        if entete in response:
            return response
        directives = {nom: list(valeurs) for nom, valeurs in settings.CSP_DIRECTIVES.items()}
        for origine in getattr(response, 'csp_origines', ()):
            for nom in ('script-src', 'frame-src'):
                if origine not in directives.setdefault(nom, []):
                    directives[nom].append(origine)
        response[entete] = '; '.join(f"{nom} {' '.join(valeurs)}" for nom, valeurs in directives.items())
        return response


class RelancesPaiementMiddleware:
    """Déclenche les relances de paiement au fil des visites (au plus une fois par heure, en tâche de fond)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith(('/static/', '/media/')):
            verifier_relances()
        return response
