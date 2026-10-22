from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from boutique.images import image_depuis_lien
from boutique.images_libres import IMAGES_LIBRES
from boutique.models import Produit


class Command(BaseCommand):
    help = ("Télécharge, compresse et attache les photos libres de droits (boutique/images_libres.py) aux produits "
            "qui n'ont pas encore de photo, avec leur crédit. Sans --appliquer : simulation.")

    def add_arguments(self, parser):
        parser.add_argument('--appliquer', action='store_true', help="Télécharge et enregistre réellement les photos.")

    def handle(self, *args, appliquer=False, **options):
        produits = {p.slug: p for p in Produit.objects.filter(slug__in=IMAGES_LIBRES)}
        ajoutees = deja = absents = erreurs = 0
        for slug, photo in IMAGES_LIBRES.items():
            produit = produits.get(slug)
            if produit is None:
                absents += 1
                self.stdout.write(f"  - {slug} : produit absent (chargez d'abord le catalogue)")
                continue
            if produit.image:
                deja += 1
                continue                             # jamais de remplacement d'une photo existante
            if not appliquer:
                self.stdout.write(f"  + {slug} : {photo['credit']}")
                ajoutees += 1
                continue
            try:
                contenu = image_depuis_lien(photo['url'])
            except ValidationError as erreur:
                erreurs += 1
                self.stdout.write(f"  ! {slug} : {' '.join(erreur.messages)}")
                continue
            produit.image.save(f"{slug}.webp", contenu, save=False)
            produit.credit_image, produit.source_image = photo['credit'], photo['source']
            produit.save(update_fields=['image', 'credit_image', 'source_image'])
            ajoutees += 1
            self.stdout.write(f"  + {slug}")

        bilan = (f"{ajoutees} photo(s) {'ajoutée(s)' if appliquer else 'à ajouter'}, {deja} produit(s) ayant déjà une photo, "
                 f"{absents} produit(s) absent(s), {erreurs} erreur(s).")
        if appliquer:
            self.stdout.write(self.style.SUCCESS(bilan))
        else:
            self.stdout.write(self.style.WARNING(f"SIMULATION - {bilan}\nRelancez avec --appliquer pour importer les photos."))
