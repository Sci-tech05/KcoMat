from django.core.management.base import BaseCommand

from boutique.catalogue import charger_catalogue, nombre_produits


class Command(BaseCommand):
    help = ("Charge le catalogue de composants (Électronique, Électricité, Capteurs, Moteurs & Robotique, LED & Afficheurs, Boutons & Interrupteurs, Relais, Résistances). "
            "Les produits créés sont masqués avec un stock à 0 : ajoutez image et quantité puis publiez-les depuis l'admin.")

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help="Réécrit aussi les textes des produits du catalogue déjà présents (prix, stock et images conservés).")

    def handle(self, *args, **options):
        crees, maj, inchangees = charger_catalogue(force=options['force'])
        self.stdout.write(self.style.SUCCESS(
            f"Catalogue ({nombre_produits()} produits) : {crees} créé(s), {maj} mis à jour, {inchangees} inchangé(s)."
        ))
