from django.apps import AppConfig


class BoutiqueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'boutique'
    verbose_name = "Boutique"

    def ready(self):
        # composant du catalogue supprimé dans l'admin : mémorisé pour ne pas revenir au prochain chargement
        from django.db.models.signals import post_delete
        from .catalogue import memoriser_retrait
        post_delete.connect(memoriser_retrait, sender='boutique.Produit', dispatch_uid='boutique.memoriser_retrait')
