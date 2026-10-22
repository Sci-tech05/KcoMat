"""
Compression des images envoyées sur le site (tous les ImageField : boutique, services, formations,
carrières, projets, équipe, témoignages, partenaires).

Seule la version compressée est conservée : redressée (EXIF), réduite, encodée en WebP, sans
métadonnées (GPS, appareil). L'original n'est jamais écrit sur le disque.
- À l'envoi : signal pre_save (core.apps) → `compresser_envoi`.
- Images déjà en ligne : `python manage.py compresser_images`.
- Image remplacée, effacée ou élément supprimé : l'ancien fichier est supprimé du disque
  (`memoriser_anciennes_images` / `supprimer_images_remplacees` / `supprimer_images_de_l_element`).
"""
import logging
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models, transaction
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

COTE_MAX = 1600       # px, côté le plus long (bannières de formations, offres, services)
QUALITE_WEBP = 80

# Réglages par modèle (app_label.modele) ; les autres utilisent COTE_MAX et gardent la transparence
REGLAGES = {
    'boutique.produit': {'cote_max': 1200, 'fond_blanc': True},
    'boutique.imageproduit': {'cote_max': 1200, 'fond_blanc': True},
    'core.teammember': {'cote_max': 800},
    'core.temoignage': {'cote_max': 600},
    'partenariats.partenaire': {'cote_max': 600},   # logos : transparence conservée
}


def reglages(instance):
    return REGLAGES.get(instance._meta.label_lower, {})


def compresser(fichier, cote_max=COTE_MAX, fond_blanc=False):
    """
    Renvoie un ContentFile WebP compressé, ou None pour un GIF animé (laissé tel quel).
    fond_blanc=True aplatit la transparence sur du blanc (photos produits) ; sinon elle est conservée.
    """
    try:
        with Image.open(fichier) as img:
            if getattr(img, 'is_animated', False):
                return None
            img = ImageOps.exif_transpose(img)
            transparent = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            if transparent and fond_blanc:
                img = img.convert('RGBA')
                fond = Image.new('RGB', img.size, (255, 255, 255))
                fond.paste(img, mask=img.getchannel('A'))
                img = fond
            else:
                img = img.convert('RGBA' if transparent else 'RGB')
            img.thumbnail((cote_max, cote_max), Image.LANCZOS)
            sortie = BytesIO()
            img.save(sortie, 'WEBP', quality=QUALITE_WEBP, method=6)  # sans métadonnées EXIF / GPS
    except (UnidentifiedImageError, OSError):
        raise ValidationError("Fichier image illisible ou format non pris en charge.")
    return ContentFile(sortie.getvalue())


def nom_webp(nom):
    return Path(nom).with_suffix('.webp').name


def champs_image(modele):
    return [champ for champ in modele._meta.fields if isinstance(champ, models.ImageField)]


def compresser_envoi(sender, instance, raw=False, **kwargs):
    """pre_save : remplace chaque image tout juste envoyée (pas encore écrite) par sa version WebP."""
    if raw:
        return
    for champ in champs_image(sender):
        fichier = getattr(instance, champ.attname)
        if not fichier or fichier._committed:
            continue
        try:
            contenu = compresser(fichier, **reglages(instance))
        except ValidationError:
            logger.warning("Compression impossible pour %s : image enregistrée telle quelle", fichier.name, exc_info=True)
            continue
        if contenu is not None:
            fichier.save(nom_webp(fichier.name), contenu, save=False)


def _supprimer_si_inutilise(modele, champ, nom):
    """Supprime le fichier une fois la transaction validée, s'il n'est plus utilisé par aucun élément."""
    def supprimer():
        if not modele._default_manager.filter(**{champ.attname: nom}).exists():
            champ.storage.delete(nom)
    transaction.on_commit(supprimer)


def memoriser_anciennes_images(sender, instance, raw=False, **kwargs):
    """pre_save : retient les images actuellement enregistrées, pour supprimer celles qui seront remplacées."""
    champs = champs_image(sender)
    if raw or not champs or instance.pk is None:
        return
    instance._images_avant = sender._default_manager.filter(pk=instance.pk).values(
        *[champ.attname for champ in champs]).first() or {}


def supprimer_images_remplacees(sender, instance, raw=False, **kwargs):
    """post_save : supprime du disque l'image remplacée ou effacée (case « Effacer »)."""
    avant = getattr(instance, '_images_avant', None)
    if raw or not avant:
        return
    del instance._images_avant
    for champ in champs_image(sender):
        ancien = avant.get(champ.attname)
        if ancien and ancien != getattr(instance, champ.attname).name:
            _supprimer_si_inutilise(sender, champ, ancien)


def supprimer_images_de_l_element(sender, instance, **kwargs):
    """post_delete : supprime du disque les images de l'élément supprimé."""
    for champ in champs_image(sender):
        fichier = getattr(instance, champ.attname)
        if fichier:
            _supprimer_si_inutilise(sender, champ, fichier.name)
