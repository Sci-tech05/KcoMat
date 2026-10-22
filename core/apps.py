from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = "Site & contenus"

    def ready(self):
        # Libellés français des champs (admin, formulaires) : voir core/labels.py
        from .labels import appliquer_libelles
        appliquer_libelles()

        # Toute image envoyée (admin, formulaires) est compressée en WebP avant d'être écrite : voir core/images.py
        from django.db.models.signals import pre_save
        from .images import compresser_envoi
        pre_save.connect(compresser_envoi, dispatch_uid='core.compresser_images_envoyees')
