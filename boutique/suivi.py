"""Suivi de commande : e-mail au client quand l'équipe fait avancer sa commande."""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)

# statuts qui déclenchent un e-mail au client (le paiement a déjà sa facture)
STATUTS_NOTIFIES = {
    'en_preparation': 'Votre commande est en préparation',
    'expediee': 'Votre commande est en route',
    'livree': 'Votre commande est livrée',
    'annulee': 'Votre commande a été annulée',
}


def lien_suivi(commande, request=None):
    chemin = reverse('boutique:suivi_commande', args=[commande.pk])
    base = (getattr(settings, 'FEDAPAY_APP_URL', '') or '').rstrip('/')
    if base:
        return base + chemin
    return request.build_absolute_uri(chemin) if request else chemin


def envoyer_email_suivi(commande, request=None):
    """Prévient le client du nouveau statut. Renvoie True si un e-mail est parti."""
    sujet = STATUTS_NOTIFIES.get(commande.statut)
    destinataire = (commande.email or '').strip()
    if not sujet or not destinataire:
        return False
    contexte = {'commande': commande, 'titre': sujet, 'lien': lien_suivi(commande, request), 'KCOMAT': settings.KCOMAT_INFO}
    message = EmailMultiAlternatives(
        subject=f'KcoMat — {sujet} (#{commande.pk})',
        body=render_to_string('boutique/emails/suivi.txt', contexte),
        to=[destinataire],
    )
    message.attach_alternative(render_to_string('boutique/emails/suivi.html', contexte), 'text/html')
    message.send(fail_silently=False)
    return True
