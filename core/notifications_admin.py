"""E-mail à l'administrateur principal (KCOMAT_INFO['email']) à chaque demande ou paiement d'un client.

Un échec d'envoi n'empêche jamais l'action du client : il est seulement journalisé.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

# couleur de l'en-tête et pictogramme selon l'événement
STYLES = {
    'contact': ('#2563EB', '✉️'),
    'candidature': ('#7C3AED', '📄'),
    'inscription': ('#0891B2', '🎓'),
    'paiement': ('#059669', '💰'),
    'commande': ('#059669', '🛒'),
    'partenariat': ('#D97706', '🤝'),
    'service': ('#DB2777', '🛠️'),
}


def _base_url(request=None):
    base = (getattr(settings, 'FEDAPAY_APP_URL', '') or '').rstrip('/')
    if base:
        return base
    return request.build_absolute_uri('/').rstrip('/') if request else ''


def lien_admin(objet, request=None):
    """Lien absolu vers la fiche de l'objet dans l'admin ('' si introuvable)."""
    try:
        chemin = reverse(f'admin:{objet._meta.app_label}_{objet._meta.model_name}_change', args=[objet.pk])
    except NoReverseMatch:
        return ''
    return _base_url(request) + chemin


def notifier_admin(*, type_evenement, sujet, titre, intro, details, message='', objet=None,
                   repondre_a='', request=None):
    """
    Envoie l'e-mail à l'admin principal. Renvoie True si l'e-mail est parti.

    details : liste de (libellé, valeur) ; les valeurs vides sont ignorées.
    message : texte libre du client (affiché en citation).
    repondre_a : adresse du client, utilisée en « Répondre à ».
    """
    destinataire = settings.KCOMAT_INFO.get('email')
    if not destinataire:
        return False
    couleur, picto = STYLES.get(type_evenement, ('#2563EB', '🔔'))
    contexte = {
        'titre': titre,
        'intro': intro,
        'details': [(libelle, valeur) for libelle, valeur in details if valeur not in (None, '')],
        'message': message,
        'lien_admin': lien_admin(objet, request) if objet is not None else '',
        'couleur': couleur,
        'picto': picto,
        'date': timezone.localtime(),
        'repondre_a': repondre_a,
        'KCOMAT': settings.KCOMAT_INFO,
    }
    try:
        email = EmailMultiAlternatives(
            subject=f'[KcoMat] {sujet}',
            body=render_to_string('emails/admin_notification.txt', contexte),
            to=[destinataire],
            reply_to=[repondre_a] if repondre_a else None,
        )
        email.attach_alternative(render_to_string('emails/admin_notification.html', contexte), 'text/html')
        email.send(fail_silently=False)
        return True
    except Exception:
        # avertissement (pas une erreur) : inutile de prévenir l'admin… par un e-mail qui ne partirait pas
        logger.warning("Notification admin « %s » non envoyée", sujet, exc_info=True)
        return False
