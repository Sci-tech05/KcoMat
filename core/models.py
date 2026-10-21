from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TeamMember(models.Model):
    nom = models.CharField(max_length=100)
    poste = models.CharField(max_length=150)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='team/', blank=True, null=True)
    linkedin = models.URLField(blank=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre']
        verbose_name = "Membre de l'équipe"
        verbose_name_plural = "Membres de l'équipe"

    def __str__(self):
        return f"{self.nom} — {self.poste}"


class Temoignage(models.Model):
    nom = models.CharField(max_length=100)
    poste = models.CharField(max_length=150, blank=True)
    texte = models.TextField()
    note = models.PositiveSmallIntegerField(default=5)
    photo = models.ImageField(upload_to='temoignages/', blank=True, null=True)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Témoignage"

    def __str__(self):
        return f"{self.nom} ({self.note}/5)"


class Statistique(models.Model):
    libelle = models.CharField(max_length=100)
    valeur = models.CharField(max_length=50)
    icone = models.CharField(max_length=50, default='star', help_text="Nom icône HeroIcons")
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"{self.valeur} {self.libelle}"


class ContactMessage(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20, blank=True)
    sujet = models.CharField(max_length=200)
    message = models.TextField()
    lu = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"

    def __str__(self):
        return f"{self.nom} — {self.sujet}"


class Avis(models.Model):
    """Avis d'un client (note 1 à 5 + commentaire) sur un composant ou une formation.

    Un seul avis par client et par article : un nouvel envoi remplace l'ancien.
    Publié tout de suite ; l'admin peut le masquer en décochant « Publié ».
    """
    NOTES = [(n, f'{n} étoile{"s" if n > 1 else ""}') for n in range(1, 6)]

    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    objet = GenericForeignKey('content_type', 'object_id')
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='avis')
    note = models.PositiveSmallIntegerField(choices=NOTES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField(max_length=1500, blank=True)
    achat_verifie = models.BooleanField(default=False, help_text="Le client a payé ce composant ou cette formation.")
    publie = models.BooleanField('Publié', default=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-modifie_le']
        verbose_name = 'Avis client'
        verbose_name_plural = 'Avis clients'
        constraints = [
            models.UniqueConstraint(fields=['content_type', 'object_id', 'utilisateur'], name='un_avis_par_client_et_article'),
        ]
        indexes = [models.Index(fields=['content_type', 'object_id', 'publie'])]

    def __str__(self):
        return f'{self.note}★ — {self.utilisateur} sur {self.objet}'

    @property
    def auteur(self):
        """Prénom + initiale du nom si renseignés (jamais le nom complet), sinon le pseudo."""
        u = self.utilisateur
        if u.first_name:
            return f'{u.first_name} {u.last_name[:1]}.' if u.last_name else u.first_name
        return u.get_username()
