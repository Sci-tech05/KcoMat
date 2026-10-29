"""Envoi des notifications Web Push (VAPID) aux abonnés."""
import json
import logging
import threading

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from .models import AbonnementPush, NotificationPush

logger = logging.getLogger(__name__)

ECHECS_MAX = 5           # abonnement désactivé après 5 échecs consécutifs
TTL_SECONDES = 3 * 24 * 3600   # le service push conserve le message 3 jours si le téléphone est éteint


def push_configure():
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def _url_absolue(url):
    if not url:
        return '/'
    if url.startswith('http'):
        return url
    base = (getattr(settings, 'FEDAPAY_APP_URL', '') or '').rstrip('/')
    return f"{base}{url}" if base else url


def envoyer(notification, abonnements=None):
    """Envoie une NotificationPush (déjà enregistrée) aux abonnés concernés. Met à jour ses compteurs.

    abonnements : queryset restreignant les destinataires (ex. test sur quelques appareils).
    """
    if not push_configure():
        logger.error("Notifications push non configurées (VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY manquantes).")
        return notification
    from pywebpush import WebPushException, webpush

    payload = json.dumps({
        'title': notification.titre,
        'body': notification.message,
        'url': notification.url or '/',
        'image': _url_absolue(notification.image) if notification.image else None,
        'tag': f"kcomat-{notification.type_notification}-{notification.objet_id or notification.pk}",
    })
    claims = {'sub': f"mailto:{settings.VAPID_CLAIM_EMAIL}"}
    envoyes = echecs = expires = 0

    destinataires = abonnements if abonnements is not None else AbonnementPush.objects.all()
    for abonnement in destinataires.filter(actif=True):
        if not abonnement.accepte(notification.type_notification):
            continue
        try:
            webpush(
                subscription_info={'endpoint': abonnement.endpoint,
                                   'keys': {'p256dh': abonnement.p256dh, 'auth': abonnement.auth}},
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=dict(claims),
                ttl=TTL_SECONDES,
                timeout=10,
            )
        except WebPushException as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            if status in (404, 410):          # abonnement révoqué ou expiré côté navigateur
                abonnement.delete()
                expires += 1
                continue
            echecs += 1
            abonnement.echecs += 1
            abonnement.actif = abonnement.echecs < ECHECS_MAX
            abonnement.save(update_fields=['echecs', 'actif'])
            logger.warning("Push refusé (HTTP %s) pour l'abonnement #%s : %s", status, abonnement.pk, exc)
        except Exception:
            echecs += 1
            logger.exception("Erreur d'envoi push pour l'abonnement #%s", abonnement.pk)
        else:
            envoyes += 1
            abonnement.echecs = 0
            abonnement.dernier_envoi = timezone.now()
            abonnement.save(update_fields=['echecs', 'dernier_envoi'])

    NotificationPush.objects.filter(pk=notification.pk).update(envoyes=envoyes, echecs=echecs, expires=expires)
    notification.envoyes, notification.echecs, notification.expires = envoyes, echecs, expires
    logger.info("Notification « %s » : %s reçue(s), %s échec(s), %s expiré(s)", notification.titre, envoyes, echecs, expires)
    return notification


def _envoyer_en_tache_de_fond(notification_id):
    close_old_connections()
    try:
        notification = NotificationPush.objects.get(pk=notification_id)
        envoyer(notification)
    except Exception:
        logger.exception("Envoi de la notification #%s impossible", notification_id)
    finally:
        close_old_connections()


def planifier(notification):
    """Envoie après validation de la transaction ; en tâche de fond sauf si PUSH_ASYNC=False (tests)."""
    def lancer():
        if getattr(settings, 'PUSH_ASYNC', True):
            threading.Thread(target=_envoyer_en_tache_de_fond, args=(notification.pk,), daemon=True).start()
        else:
            envoyer(notification)
    transaction.on_commit(lancer)
    return notification


def notifier(type_notification, titre, message, url, image='', objet_id=None):
    notification = NotificationPush.objects.create(
        type_notification=type_notification, titre=titre[:120], message=message[:240],
        url=url or '/', image=image or '', objet_id=objet_id,
    )
    return planifier(notification)


# --------------------------------------------------------------------------- publications
def _contenu(instance):
    """(type, titre, message, url, image) pour une offre, une formation, un projet ou un webinaire."""
    from carrieres.models import Offre
    from formations.models import Formation
    from projets.models import Projet
    from webinaires.models import Webinaire
    from django.urls import reverse
    from django.utils.text import Truncator

    image = getattr(instance, 'image', None)
    image_url = image.url if image else (getattr(instance, 'miniature', '') or '')   # projets : miniature YouTube
    if isinstance(instance, Offre):
        libelle = {'stage': 'Nouveau stage', 'emploi': "Nouvelle offre d'emploi",
                   'freelance': 'Nouvelle mission freelance'}.get(instance.type_offre, 'Nouvelle offre')
        message = instance.resume
        if instance.prix_min() is not None:
            message = f"{message} · Dès {instance.prix_min():,} FCFA".replace(',', ' ')
        return ('offre', f"{libelle} : {instance.titre}", message,
                reverse('carrieres:detail', args=[instance.slug]), image_url)
    if isinstance(instance, Formation):
        prix = f" · {int(instance.prix):,} FCFA".replace(',', ' ') if instance.prix else ''
        return ('formation', f"Nouvelle formation : {instance.titre}",
                Truncator(instance.description_courte).chars(180) + prix,
                reverse('formations:detail', args=[instance.slug]), image_url)
    if isinstance(instance, Webinaire):
        from django.utils import formats, timezone, translation
        debut = timezone.localtime(instance.date_debut)
        with translation.override('fr'):
            quand = formats.date_format(debut, 'l j F')
        return ('webinaire', f"Nouveau webinaire : {instance.titre}",
                f"{quand.capitalize()} à {debut:%H:%M}, en ligne et gratuit. Réservez votre place !",
                reverse('webinaires:detail', args=[instance.slug]), image_url)
    if isinstance(instance, Projet):
        return ('projet', f"Nouveau projet réalisé : {instance.titre}",
                Truncator(instance.description_courte).chars(200),
                reverse('projets:detail', args=[instance.slug]), image_url)
    return None


def deja_notifie(instance):
    contenu = _contenu(instance)
    return bool(contenu) and NotificationPush.objects.filter(type_notification=contenu[0], objet_id=instance.pk).exists()


def notifier_publication(instance, forcer=False):
    """Prévient les abonnés qu'un contenu vient d'être publié (une seule fois, sauf forcer=True)."""
    contenu = _contenu(instance)
    if not contenu or (not forcer and deja_notifie(instance)):
        return None
    type_notification, titre, message, url, image = contenu
    return notifier(type_notification, titre, message, url, image, objet_id=instance.pk)
