from django.conf import settings


def site_context(request):
    """Injecte les infos KcoMat dans tous les templates."""
    # URL publique du site (APP_URL) pour canonical / Open Graph / sitemap,
    # sinon celle de la requête courante.
    site_url = (settings.FEDAPAY_APP_URL or request.build_absolute_uri('/')).rstrip('/')
    return {
        'KCOMAT': settings.KCOMAT_INFO,
        'FEDAPAY_PUBLIC_KEY': settings.FEDAPAY_PUBLIC_KEY,
        'SITE_URL': site_url,
        'CANONICAL_URL': f"{site_url}{request.path}",
        'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY,
        # Après création de compte : ouvre automatiquement la proposition de notifications
        'PROPOSER_NOTIFICATIONS': request.session.pop('proposer_notifications', False) if hasattr(request, 'session') else False,
    }
