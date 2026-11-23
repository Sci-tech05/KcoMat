"""Liens d'accès signés (e-mails de relance) : ouvrir le paiement d'une commande, d'une inscription
ou d'une demande sans compte et depuis un autre appareil que celui qui l'a créée.

Le jeton ne vaut que pour l'objet qu'il désigne et expire au bout de DUREE ; une fois validé, l'accès
est mémorisé dans la session pour les pages suivantes (retour de FedaPay, facture…).
"""
from urllib.parse import urlencode

from django.core import signing

SEL = 'kcomat-acces-paiement'
DUREE = 45 * 24 * 3600
SESSION_KEY = 'kcomat_acces_signes'


def _cle(objet):
    return f"{objet._meta.label_lower}:{objet.pk}"


def jeton(objet):
    return signing.dumps(_cle(objet), salt=SEL)


def avec_jeton(url, objet):
    return f"{url}{'&' if '?' in url else '?'}{urlencode({'acces': jeton(objet)})}"


def acces_autorise(request, objet):
    """True si la session a déjà été ouverte pour cet objet, ou si l'URL porte un jeton valide pour lui."""
    cle = _cle(objet)
    autorises = request.session.get(SESSION_KEY, [])
    if cle in autorises:
        return True
    valeur = request.GET.get('acces')
    if not valeur:
        return False
    try:
        if signing.loads(valeur, salt=SEL, max_age=DUREE) != cle:
            return False
    except signing.BadSignature:
        return False
    request.session[SESSION_KEY] = autorises + [cle]
    return True
