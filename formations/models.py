from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class CategorieFormation(models.Model):
    nom = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    icone = models.CharField(max_length=50, default='academic-cap')
    couleur = models.CharField(max_length=20, default='blue')

    class Meta:
        verbose_name = "Catégorie formation"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class Formation(models.Model):
    NIVEAU_CHOICES = [
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
    ]
    titre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    categorie = models.ForeignKey(CategorieFormation, on_delete=models.SET_NULL, null=True, related_name='formations')
    description_courte = models.CharField(max_length=300)
    description = models.TextField()
    image = models.ImageField(upload_to='formations/', blank=True, null=True)
    duree = models.CharField(max_length=100, default='À définir')
    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES, default='debutant')
    prix = models.DecimalField(max_digits=10, decimal_places=0)
    prix_avec_base = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True,
                                         help_text="Prix si formé en domotique (ex: MicroPython)")
    places_disponibles = models.PositiveIntegerField(default=20)
    actif = models.BooleanField(default=True)
    nouveau = models.BooleanField(default=False)
    en_vedette = models.BooleanField(default=False)
    objectifs = models.TextField(blank=True, help_text="Un objectif par ligne")
    prerequis = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['titre']
        verbose_name = "Formation"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre

    def get_objectifs_list(self):
        return [o.strip() for o in self.objectifs.split('\n') if o.strip()]

    def get_prerequis_list(self):
        if self.prerequis:
            return [p.strip() for p in self.prerequis.split('\n') if p.strip()]
        return []


class Inscription(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de paiement'),
        ('frais_payes', 'Frais d\'inscription payés'),
        ('complet', 'Paiement complet'),
        ('annule', 'Annulé'),
    ]
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='inscriptions')
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    niveau_actuel = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    # Paiement frais inscription (2000 FCFA)
    fedapay_frais_id = models.CharField(max_length=100, blank=True)
    frais_payes_le = models.DateTimeField(null=True, blank=True)
    # Paiement formation
    fedapay_formation_id = models.CharField(max_length=100, blank=True)
    formation_payee_le = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Inscription"

    def __str__(self):
        return f"{self.prenom} {self.nom} — {self.formation.titre}"

    def montant_inscription(self):
        from django.conf import settings
        return settings.KCOMAT_INFO['frais_inscription']
