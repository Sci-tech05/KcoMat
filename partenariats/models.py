from django.db import models


class Partenaire(models.Model):
    TYPE_CHOICES = [
        ('entreprise', 'Entreprise'),
        ('institution', 'Institution'),
        ('ong', 'ONG / Association'),
        ('autre', 'Autre'),
    ]
    nom = models.CharField(max_length=200)
    type_partenaire = models.CharField(max_length=20, choices=TYPE_CHOICES, default='entreprise')
    logo = models.ImageField(upload_to='partenaires/', blank=True, null=True)
    site_web = models.URLField(blank=True)
    description = models.TextField(blank=True)
    actif = models.BooleanField(default=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = "Partenaire"

    def __str__(self):
        return self.nom


class DemandePartenariat(models.Model):
    nom_organisation = models.CharField(max_length=200)
    type_organisation = models.CharField(max_length=100)
    nom_contact = models.CharField(max_length=150)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    site_web = models.URLField(blank=True)
    description_projet = models.TextField()
    type_partenariat_souhaite = models.CharField(max_length=200)
    traite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande de partenariat"
        verbose_name_plural = "Demandes de partenariat"

    def __str__(self):
        return f"{self.nom_organisation} — {self.nom_contact}"
