import shutil
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from PIL import Image

from core.images import COTE_MAX, champs_image, compresser, nom_webp, reglages


def ko(octets):
    return f"{octets / 1024:,.0f} Ko".replace(',', ' ')


class Command(BaseCommand):
    help = ("Compresse en WebP les images déjà en ligne (produits, services, formations, offres, projets, équipe, "
            "témoignages, partenaires) et SUPPRIME les originaux. Sans --appliquer : simulation, rien n'est modifié.")

    def add_arguments(self, parser):
        parser.add_argument('--appliquer', action='store_true',
                            help="Effectue réellement la compression et supprime les originaux.")

    def handle(self, *args, appliquer=False, **options):
        avant = apres = traitees = 0
        for modele in apps.get_models():
            for champ in champs_image(modele):
                for instance in modele.objects.exclude(**{champ.attname: ''}).exclude(**{f'{champ.attname}__isnull': True}):
                    fichier = getattr(instance, champ.attname)
                    resultat = self.traiter(instance, champ, fichier, appliquer)
                    if resultat:
                        avant += resultat[0]
                        apres += resultat[1]
                        traitees += 1

        if appliquer and traitees:
            # copies redimensionnées / aperçus de partage des anciens fichiers : recréés à la demande
            for cache in ('cache/webp', 'cache/og'):
                shutil.rmtree(Path(settings.MEDIA_ROOT, cache), ignore_errors=True)

        bilan = f"{traitees} image(s) : {ko(avant)} -> {ko(apres)} (gain {ko(avant - apres)})."
        if appliquer:
            self.stdout.write(self.style.SUCCESS(f"Compression terminée, originaux supprimés. {bilan}"))
        else:
            self.stdout.write(self.style.WARNING(f"SIMULATION — rien n'a été modifié. {bilan}\n"
                                                 "Relancez avec --appliquer pour compresser et supprimer les originaux."))

    def traiter(self, instance, champ, fichier, appliquer):
        etiquette = f"{instance._meta.label} #{instance.pk} {fichier.name}"
        try:
            chemin = Path(fichier.path)
        except (ValueError, NotImplementedError):
            return None
        if not chemin.exists():
            self.stdout.write(f"  ! introuvable : {etiquette}")
            return None
        options = reglages(instance)
        if chemin.suffix.lower() == '.webp':
            with Image.open(chemin) as img:
                if max(img.size) <= options.get('cote_max', COTE_MAX):
                    return None                      # déjà compressée
        try:
            with chemin.open('rb') as source:
                contenu = compresser(source, **options)
        except ValidationError:
            self.stdout.write(f"  ! illisible, laissée telle quelle : {etiquette}")
            return None
        if contenu is None:
            return None                              # GIF animé : laissé tel quel
        taille_avant = chemin.stat().st_size
        if contenu.size >= taille_avant and chemin.suffix.lower() == '.webp':
            return None
        self.stdout.write(f"  {etiquette} : {ko(taille_avant)} -> {ko(contenu.size)}")
        if appliquer:
            ancien_nom = fichier.name
            fichier.save(nom_webp(ancien_nom), contenu, save=False)
            # update() plutôt que save() : pas de signaux (notifications de publication, etc.)
            type(instance).objects.filter(pk=instance.pk).update(**{champ.attname: fichier.name})
            encore_utilise = type(instance).objects.filter(**{champ.attname: ancien_nom}).exists()
            if fichier.name != ancien_nom and not encore_utilise:
                fichier.storage.delete(ancien_nom)
        return taille_avant, contenu.size
