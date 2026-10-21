"""Suivi de commande : e-mail au client quand l'équipe fait avancer sa commande."""
import logging
import smtplib
import socket

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


def raison_echec_email(erreur):
    """Explication courte et utile d'un échec d'envoi, pour le message affiché dans l'admin."""
    if isinstance(erreur, smtplib.SMTPAuthenticationError):
        return ("Gmail refuse l'identifiant ou le mot de passe d'application (EMAIL_HOST_PASSWORD). "
                "Générez un nouveau mot de passe d'application Google et mettez-le à jour dans le .env.")
    if isinstance(erreur, smtplib.SMTPRecipientsRefused):
        return "l'adresse e-mail du client est refusée par le serveur."
    if isinstance(erreur, smtplib.SMTPServerDisconnected):
        # Gmail coupe la connexion après avoir refusé le mot de passe (535 puis déconnexion)
        return ("Gmail a coupé la connexion, le plus souvent parce que le mot de passe d'application "
                "(EMAIL_HOST_PASSWORD) est refusé. Générez-en un nouveau et mettez à jour le .env.")
    if isinstance(erreur, (socket.timeout, TimeoutError, ConnectionError, smtplib.SMTPConnectError)):
        return "le serveur d'envoi (SMTP) est injoignable."
    return f"erreur {type(erreur).__name__} (détail dans les logs)."
