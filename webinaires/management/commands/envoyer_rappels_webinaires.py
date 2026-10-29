"""Rappels « 20 min avant » des webinaires (push + e-mail aux inscrits).

    python manage.py envoyer_rappels_webinaires            # une vérification (tâche planifiée)
    python manage.py envoyer_rappels_webinaires --boucle   # vérifie chaque minute (« Always-on task » PythonAnywhere)

Les visites du site déclenchent aussi ces rappels : cette commande garantit l'envoi même sans visite.
"""
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from webinaires.rappels import envoyer_rappels_dus


class Command(BaseCommand):
    help = "Envoie les rappels des webinaires qui commencent dans 20 minutes ou moins."

    def add_arguments(self, parser):
        parser.add_argument('--boucle', action='store_true', help="Vérifie en continu, toutes les 60 secondes.")

    def handle(self, *args, boucle=False, **options):
        while True:
            close_old_connections()
            for webinaire in envoyer_rappels_dus():
                self.stdout.write(f"Rappel envoyé : {webinaire.titre}")
            if not boucle:
                return
            time.sleep(60)
