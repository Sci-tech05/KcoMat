import base64

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génère une paire de clés VAPID pour les notifications push (à copier dans le .env du serveur)."

    def handle(self, *args, **options):
        from cryptography.hazmat.primitives import serialization
        from py_vapid import Vapid01

        vapid = Vapid01()
        vapid.generate_keys()
        b64 = lambda data: base64.urlsafe_b64encode(data).rstrip(b'=').decode()
        privee = b64(vapid.private_key.private_numbers().private_value.to_bytes(32, 'big'))
        publique = b64(vapid.public_key.public_bytes(serialization.Encoding.X962,
                                                     serialization.PublicFormat.UncompressedPoint))
        self.stdout.write("Ajoutez ces lignes au fichier .env (la clé privée est SECRÈTE) :\n")
        self.stdout.write(f"VAPID_PUBLIC_KEY={publique}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={privee}")
        self.stdout.write("VAPID_CLAIM_EMAIL=kcomat0@gmail.com\n")
        self.stdout.write(self.style.WARNING(
            "Attention : changer de clés invalide les abonnements existants (les visiteurs devront se réabonner)."))
