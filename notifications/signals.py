"""Notification automatique des abonnés quand une offre, une formation, un projet ou un webinaire est publié."""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from carrieres.models import Offre
from formations.models import Formation
from projets.models import Projet
from webinaires.models import Webinaire

from .push import notifier_publication

MODELES_SUIVIS = (Offre, Formation, Projet, Webinaire)


def _etait_publie(sender, instance):
    if not instance.pk:
        return False
    return sender.objects.filter(pk=instance.pk, actif=True).exists()


@receiver(pre_save)
def memoriser_etat_publication(sender, instance, **kwargs):
    if sender in MODELES_SUIVIS and not kwargs.get('raw'):
        instance._etait_publie = _etait_publie(sender, instance)


@receiver(post_save)
def notifier_si_publie(sender, instance, created, **kwargs):
    if sender not in MODELES_SUIVIS or kwargs.get('raw') or not instance.actif:
        return
    if getattr(instance, '_etait_publie', False):
        return                      # déjà en ligne : simple modification, pas de nouvelle annonce
    if getattr(instance, 'est_cloturee', False):
        return                      # offre dont la date limite est passée, webinaire terminé
    notifier_publication(instance)
