from django.contrib.auth.models import User
from django.db import models


class AbonnementPush(models.Model):
    """Un navigateur / téléphone abonné aux notifications du site (Web Push)."""
    endpoint = models.CharField("Adresse du service push", max_length=1000, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='abonnements_push', verbose_name="Compte")
    offres = models.BooleanField("Offres d'emploi & stages", default=True)
    formations = models.BooleanField("Formations", default=True)
    projets = models.BooleanField("Projets réalisés", default=True)
    appareil = models.CharField("Appareil", max_length=120, blank=True)
    actif = models.BooleanField(default=True)
    echecs = models.PositiveSmallIntegerField("Échecs consécutifs", default=0)
    created_at = models.DateTimeField("Abonné le", auto_now_add=True)
    dernier_envoi = models.DateTimeField("Dernière notification reçue", null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Abonné aux notifications"
        verbose_name_plural = "Abonnés aux notifications"

    def __str__(self):
        qui = self.utilisateur.get_username() if self.utilisateur_id else 'Visiteur'
        return f"{qui} · {self.appareil or 'navigateur'}"

    def accepte(self, type_notification):
        return {'offre': self.offres, 'formation': self.formations, 'projet': self.projets}.get(type_notification, True)


class NotificationPush(models.Model):
    """Journal des notifications envoyées (et formulaire d'envoi manuel dans l'admin)."""
    TYPE_CHOICES = [
        ('offre', "Offre d'emploi / stage"),
        ('formation', 'Formation'),
        ('projet', 'Projet réalisé'),
        ('annonce', 'Annonce'),
        ('test', 'Test'),
    ]
    type_notification = models.CharField("Type", max_length=20, choices=TYPE_CHOICES, default='annonce')
    titre = models.CharField(max_length=120)
    message = models.CharField(max_length=240, help_text="Texte court affiché sous le titre (240 caractères max).")
    url = models.CharField("Lien", max_length=500, default='/', help_text="Page ouverte au clic, ex. /formations/domotique/")
    image = models.CharField(max_length=500, blank=True, help_text="Adresse d'une image (facultatif).")
    objet_id = models.PositiveIntegerField(null=True, blank=True, editable=False)
    envoyes = models.PositiveIntegerField("Reçues", default=0, editable=False)
    echecs = models.PositiveIntegerField("Échecs", default=0, editable=False)
    expires = models.PositiveIntegerField("Abonnements expirés", default=0, editable=False)
    created_at = models.DateTimeField("Envoyée le", auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification envoyée"
        verbose_name_plural = "Notifications envoyées"

    def __str__(self):
        return self.titre
