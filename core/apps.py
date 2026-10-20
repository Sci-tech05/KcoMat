from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = "Site & contenus"

    def ready(self):
        # Libellés français des champs (admin, formulaires) : voir core/labels.py
        from .labels import appliquer_libelles
        appliquer_libelles()
