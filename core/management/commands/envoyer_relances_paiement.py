"""Relances de paiement par e-mail (tous les 3 jours ; chaque semaine pour les attestations de webinaires).

    python manage.py envoyer_relances_paiement

À programmer une fois par jour (onglet « Tasks » de PythonAnywhere). Les visites du site déclenchent
aussi ces relances : la commande garantit l'envoi même sans visite. Chaque personne n'est relancée
qu'à l'échéance, quel que soit le nombre de passages.
"""
from django.core.management.base import BaseCommand

from core.relances import envoyer_relances


class Command(BaseCommand):
    help = "Envoie par e-mail les relances de paiement arrivées à échéance."

    def handle(self, *args, **options):
        self.stdout.write(f"{envoyer_relances()} relance(s) de paiement envoyée(s).")
