from django.core.management.base import BaseCommand

from carrieres.catalogue import DOMAINES, charger_catalogue


class Command(BaseCommand):
    help = ("Charge le catalogue d'offres prérédigées (stage / emploi / freelance × domaines). "
            "Les offres créées sont masquées : ajoutez une image puis publiez-les depuis l'admin.")

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help="Réécrit aussi les textes des offres du catalogue déjà présentes.")

    def handle(self, *args, **options):
        crees, maj, inchangees = charger_catalogue(force=options['force'])
        self.stdout.write(self.style.SUCCESS(
            f"Catalogue ({len(DOMAINES) * 3} offres) : {crees} créée(s), {maj} mise(s) à jour, {inchangees} inchangée(s)."
        ))
