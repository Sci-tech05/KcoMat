from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = "Notifications"

    def ready(self):
        # Notification automatique des abonnés à la publication (offres, formations, projets)
        from . import signals  # noqa: F401
