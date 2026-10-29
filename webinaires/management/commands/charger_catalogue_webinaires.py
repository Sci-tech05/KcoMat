from django.core.management.base import BaseCommand

from webinaires.catalogue import charger_catalogue


class Command(BaseCommand):
    help = "Ajoute les webinaires proposés (masqués) sans toucher à ceux qui existent déjà."

    def handle(self, *args, **options):
        crees, presents = charger_catalogue()
        self.stdout.write(self.style.SUCCESS(f"{crees} webinaire(s) ajouté(s), {presents} déjà présent(s)."))
