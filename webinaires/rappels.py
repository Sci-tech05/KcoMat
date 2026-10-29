"""E-mails et rappels des webinaires : confirmation d'inscription (+ invitation agenda), rappel 20 min avant."""
import logging
import threading
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.db import close_old_connections
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.formats import date_format

from .models import RAPPEL_AVANT, Webinaire

logger = logging.getLogger(__name__)

CLE_VERIFICATION = 'kcomat:webinaires:verification-rappels'
INTERVALLE_VERIFICATION = 60   # secondes entre deux vérifications déclenchées par les visites


def _site_url():
    return (getattr(settings, 'FEDAPAY_APP_URL', '') or '').rstrip('/')


def _quand(webinaire):
    """« samedi 7 novembre 2026, de 10:00 à 11:30 (heure du Bénin) »"""
    debut, fin = timezone.localtime(webinaire.date_debut), timezone.localtime(webinaire.date_fin)
    with translation.override('fr'):
        jour = date_format(debut, 'l j F Y')
    return f"{jour}, de {debut:%H:%M} à {fin:%H:%M} (heure du Bénin)"


def _signature():
    info = settings.KCOMAT_INFO
    return f"L'équipe KcoMat\n{info['phone']} · {info['email']}\n{info['address']}"


# --------------------------------------------------------------------------- agenda (.ics)
def _ics_texte(valeur):
    return str(valeur).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def invitation_ics(webinaire):
    url = _site_url() + reverse('webinaires:detail', args=[webinaire.slug])
    fmt = '%Y%m%dT%H%M%SZ'
    utc = dt_timezone.utc
    lignes = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//KcoMat//Webinaires//FR', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
        'BEGIN:VEVENT',
        f"UID:webinaire-{webinaire.pk}@kcomat",
        f"DTSTAMP:{timezone.now().astimezone(utc).strftime(fmt)}",
        f"DTSTART:{webinaire.date_debut.astimezone(utc).strftime(fmt)}",
        f"DTEND:{webinaire.date_fin.astimezone(utc).strftime(fmt)}",
        f"SUMMARY:{_ics_texte('Webinaire KcoMat : ' + webinaire.titre)}",
        f"DESCRIPTION:{_ics_texte(webinaire.accroche + chr(10) + chr(10) + 'Salle en ligne (ouverte 10 min avant) : ' + url)}",
        f"LOCATION:{_ics_texte(url)}",
        f"URL:{url}",
        'BEGIN:VALARM', 'TRIGGER:-PT20M', 'ACTION:DISPLAY', f"DESCRIPTION:{_ics_texte(webinaire.titre)}", 'END:VALARM',
        'END:VEVENT', 'END:VCALENDAR',
    ]
    return '\r\n'.join(lignes) + '\r\n'


# --------------------------------------------------------------------------- e-mails
def confirmer_inscription(participation):
    webinaire = participation.webinaire
    url = _site_url() + reverse('webinaires:detail', args=[webinaire.slug])
    body = (
        f"Bonjour {participation.prenom},\n\n"
        f"Votre place est réservée pour le webinaire « {webinaire.titre} ».\n\n"
        f"Quand : {_quand(webinaire)}\n"
        f"Où : en ligne, sur le site KcoMat — aucune application à installer.\n"
        f"Animé par : {webinaire.intervenant}\n\n"
        f"Le bouton « Participer » apparaît sur la page du webinaire 10 minutes avant le début :\n{url}\n\n"
        f"Nous vous enverrons un rappel 20 minutes avant la séance. À la fin, votre attestation de participation "
        f"sera téléchargeable depuis la même page.\n\n"
        f"L'invitation jointe (.ics) ajoute la séance à votre agenda.\n\n"
        f"À très vite,\n{_signature()}"
    )
    message = EmailMessage(
        subject=f"KcoMat — Inscription confirmée : {webinaire.titre}",
        body=body, to=[participation.email], reply_to=[settings.KCOMAT_INFO['email']],
    )
    message.attach(f"webinaire-kcomat-{webinaire.slug}.ics", invitation_ics(webinaire), 'text/calendar')
    message.send(fail_silently=False)


def _email_rappel(participation):
    webinaire = participation.webinaire
    debut = timezone.localtime(webinaire.date_debut)
    url = _site_url() + reverse('webinaires:salle', args=[webinaire.slug])
    body = (
        f"Bonjour {participation.prenom},\n\n"
        f"Le webinaire « {webinaire.titre} » commence dans 20 minutes, à {debut:%H:%M}.\n\n"
        f"La salle en ligne ouvre 10 minutes avant le début. Rejoignez-la ici :\n{url}\n\n"
        f"Conseils : connectez-vous avec un casque ou des écouteurs, et autorisez l'accès au micro "
        f"et à la caméra lorsque votre navigateur le demande.\n\n"
        f"À tout de suite,\n{_signature()}"
    )
    EmailMessage(
        subject=f"⏰ Dans 20 min : {webinaire.titre}",
        body=body, to=[participation.email], reply_to=[settings.KCOMAT_INFO['email']],
    ).send(fail_silently=False)


# --------------------------------------------------------------------------- rappel 20 min avant
def envoyer_rappel(webinaire):
    """Notification push (abonnés « Webinaires ») + e-mail à chaque inscrit. Renvoie le nombre d'e-mails envoyés."""
    from notifications.push import notifier, push_configure

    debut = timezone.localtime(webinaire.date_debut)
    if push_configure():
        image = webinaire.image.url if webinaire.image else ''
        notifier('webinaire_rappel', f"Dans 20 min : {webinaire.titre}",
                 f"Le webinaire commence à {debut:%H:%M}. Le bouton « Participer » s'affiche dès {timezone.localtime(webinaire.ouverture_salle):%H:%M}.",
                 reverse('webinaires:detail', args=[webinaire.slug]), image, objet_id=webinaire.pk)
    envoyes = 0
    for participation in webinaire.participations.select_related('webinaire'):
        try:
            _email_rappel(participation)
            envoyes += 1
        except Exception:
            logger.exception("Rappel webinaire #%s : e-mail impossible pour %s", webinaire.pk, participation.email)
    logger.info("Rappel du webinaire « %s » : %s e-mail(s) envoyé(s)", webinaire.titre, envoyes)
    return envoyes


def rappels_dus(maintenant=None):
    maintenant = maintenant or timezone.now()
    return Webinaire.objects.publies().filter(
        rappel_envoye_le__isnull=True, date_debut__gt=maintenant, date_debut__lte=maintenant + RAPPEL_AVANT)


def envoyer_rappels_dus(maintenant=None):
    """Envoie chaque rappel une seule fois, même si plusieurs processus vérifient en même temps."""
    maintenant = maintenant or timezone.now()
    traites = []
    for webinaire in rappels_dus(maintenant):
        if Webinaire.objects.filter(pk=webinaire.pk, rappel_envoye_le__isnull=True).update(rappel_envoye_le=maintenant):
            envoyer_rappel(webinaire)
            traites.append(webinaire)
    return traites


def _en_tache_de_fond():
    close_old_connections()
    try:
        envoyer_rappels_dus()
    except Exception:
        logger.exception("Envoi des rappels de webinaires impossible")
    finally:
        close_old_connections()


def verifier_rappels():
    """Appelé à chaque visite (au plus une fois par minute) : lance les rappels arrivés à échéance."""
    if not cache.add(CLE_VERIFICATION, 1, INTERVALLE_VERIFICATION):
        return
    try:
        if not rappels_dus().exists():
            return
    except Exception:          # base pas encore migrée, etc. : ne jamais casser une page
        logger.exception("Vérification des rappels de webinaires impossible")
        return
    if getattr(settings, 'PUSH_ASYNC', True):
        threading.Thread(target=_en_tache_de_fond, daemon=True).start()
    else:
        envoyer_rappels_dus()
