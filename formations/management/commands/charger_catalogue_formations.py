from django.core.management.base import BaseCommand

from formations.catalogue import CATALOGUE, charger_catalogue


class Command(BaseCommand):
    help = ("Charge le catalogue de formations prérédigées (une par catégorie). Les formations créées sont masquées : "
            "ajoutez une image, vérifiez le tarif puis publiez-les depuis l'admin.")

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help="Réécrit les textes des formations du catalogue déjà présentes (jamais l'image ni le statut).")

    def handle(self, *args, **options):
        crees, completees, inchangees = charger_catalogue(force=options['force'])
        self.stdout.write(self.style.SUCCESS(
            f"Catalogue ({len(CATALOGUE)} formations) : {crees} créée(s), {completees} complétée(s), {inchangees} inchangée(s)."
        ))
