import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_safe

from .models import AbonnementPush

PREFERENCES = ('offres', 'formations', 'projets', 'webinaires')


def _appareil(request):
    ua = request.META.get('HTTP_USER_AGENT', '')
    systeme = next((nom for cle, nom in (('iPhone', 'iPhone'), ('iPad', 'iPad'), ('Android', 'Android'),
                                          ('Windows', 'Windows'), ('Mac OS', 'Mac'), ('Linux', 'Linux')) if cle in ua), '')
    navigateur = next((nom for cle, nom in (('Edg/', 'Edge'), ('OPR/', 'Opera'), ('SamsungBrowser', 'Samsung Internet'),
                                            ('Firefox/', 'Firefox'), ('Chrome/', 'Chrome'), ('Safari/', 'Safari')) if cle in ua), '')
    return ' · '.join(filter(None, (systeme, navigateur)))[:120]


def _lire_json(request):
    try:
        return json.loads(request.body or b'{}')
    except (ValueError, UnicodeDecodeError):
        return None


@require_POST
def abonnement(request):
    """Enregistre (ou met à jour) l'abonnement push du navigateur. Protégé par CSRF."""
    data = _lire_json(request)
    subscription = (data or {}).get('subscription') or {}
    endpoint = str(subscription.get('endpoint') or '')
    keys = subscription.get('keys') or {}
    if not endpoint.startswith('https://') or len(endpoint) > 1000 or not keys.get('p256dh') or not keys.get('auth'):
        return JsonResponse({'ok': False, 'error': 'Abonnement invalide.'}, status=400)

    preferences = (data or {}).get('preferences') or {}
    valeurs = {nom: bool(preferences.get(nom, True)) for nom in PREFERENCES}
    if not any(valeurs.values()):
        return JsonResponse({'ok': False, 'error': 'Choisissez au moins un type de notification.'}, status=400)

    abonnement_obj, cree = AbonnementPush.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            'p256dh': str(keys['p256dh'])[:200], 'auth': str(keys['auth'])[:100],
            'actif': True, 'echecs': 0, 'appareil': _appareil(request), **valeurs,
            **({'utilisateur': request.user} if request.user.is_authenticated else {}),
        },
    )
    return JsonResponse({'ok': True, 'cree': cree, 'preferences': valeurs})


@require_POST
def desabonnement(request):
    data = _lire_json(request) or {}
    supprimes, _ = AbonnementPush.objects.filter(endpoint=str(data.get('endpoint') or '')).delete()
    return JsonResponse({'ok': True, 'supprime': bool(supprimes)})


@require_safe
def service_worker(request):
    """Service worker servi à la racine (portée « / ») : reçoit et affiche les notifications."""
    response = render(request, 'notifications/sw.js', {
        'icon': static('img/icons/icon-192.png'),
        'badge': static('img/icons/badge-96.png'),
        'vapid_public_key': settings.VAPID_PUBLIC_KEY,
    }, content_type='application/javascript; charset=utf-8')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


@require_safe
@cache_control(max_age=60 * 60 * 24, public=True)
def manifest(request):
    """Manifeste d'application web : installation sur l'écran d'accueil (obligatoire pour le push sur iPhone)."""
    data = {
        'name': 'KcoMat — Formations, composants & solutions tech',
        'short_name': 'KcoMat',
        'description': "Formations, offres d'emploi et de stage, composants électroniques et projets KcoMat.",
        'lang': 'fr',
        'start_url': '/?source=app',
        'scope': '/',
        'display': 'standalone',
        'background_color': '#0B1220',
        'theme_color': '#0B1220',
        'icons': [
            {'src': static('img/icons/icon-192.png'), 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('img/icons/icon-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('img/icons/icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
    return HttpResponse(json.dumps(data, ensure_ascii=False), content_type='application/manifest+json; charset=utf-8')


@csrf_exempt  # appelé par le service worker (pas de jeton CSRF) : ne peut que remplacer un abonnement existant
@require_POST
def renouvellement(request):
    data = _lire_json(request) or {}
    ancien = AbonnementPush.objects.filter(endpoint=str(data.get('ancien') or '')).first()
    subscription = data.get('subscription') or {}
    endpoint = str(subscription.get('endpoint') or '')
    keys = subscription.get('keys') or {}
    if ancien is None or not endpoint.startswith('https://') or len(endpoint) > 1000 or not keys.get('p256dh') or not keys.get('auth'):
        return JsonResponse({'ok': False}, status=400)
    AbonnementPush.objects.filter(endpoint=endpoint).exclude(pk=ancien.pk).delete()
    ancien.endpoint, ancien.p256dh, ancien.auth = endpoint, str(keys['p256dh'])[:200], str(keys['auth'])[:100]
    ancien.actif, ancien.echecs = True, 0
    ancien.save()
    return JsonResponse({'ok': True})
