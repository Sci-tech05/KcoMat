from django.conf import settings


def site_context(request):
    """Injecte les infos KcoMat dans tous les templates."""
    return {
        'KCOMAT': settings.KCOMAT_INFO,
        'FEDAPAY_PUBLIC_KEY': settings.FEDAPAY_PUBLIC_KEY,
    }
