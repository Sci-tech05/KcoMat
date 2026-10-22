from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = "Site & contenus"

    def ready(self):
        # Libellés français des champs (admin, formulaires) : voir core/labels.py
        from .labels import appliquer_libelles
        appliquer_libelles()

        # Images : compressées en WebP avant d'être écrites, anciennes versions supprimées du disque (core/images.py)
        from django.db.models.signals import post_delete, post_save, pre_save
        from . import images
        pre_save.connect(images.memoriser_anciennes_images, dispatch_uid='core.memoriser_anciennes_images')
        pre_save.connect(images.compresser_envoi, dispatch_uid='core.compresser_images_envoyees')
        post_save.connect(images.supprimer_images_remplacees, dispatch_uid='core.supprimer_images_remplacees')
        post_delete.connect(images.supprimer_images_de_l_element, dispatch_uid='core.supprimer_images_de_l_element')
