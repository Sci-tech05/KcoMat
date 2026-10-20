from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from core.video import analyser, normaliser_lien_video, valider_lien_video


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
    prerequis = models.TextField(blank=True, help_text="Un prérequis par ligne")
    programme = models.TextField(
        blank=True, help_text="Un module par ligne, au format « Titre du module : contenu » (ex. « Les bases : tension, courant, loi d'Ohm »).")
    public_cible = models.TextField("Pour qui ?", blank=True, help_text="Un profil par ligne.")
    debouches = models.TextField("Débouchés", blank=True, help_text="Un métier ou une opportunité par ligne.")
    materiel_fourni = models.TextField("Matériel fourni", blank=True, help_text="Un élément par ligne.")
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

    @staticmethod
    def _lignes(texte):
        return [l.strip().lstrip('-•*–').strip() for l in (texte or '').splitlines() if l.strip().lstrip('-•*–').strip()]

    def programme_list(self):
        """[(titre, contenu)] à partir de « Titre : contenu » (une ligne par module)."""
        modules = []
        for ligne in self._lignes(self.programme):
            titre, sep, contenu = ligne.partition(':')
            modules.append((titre.strip(), contenu.strip()) if sep and len(titre) <= 60 else (ligne, ''))
        return modules

    def public_list(self):
        return self._lignes(self.public_cible)

    def debouches_list(self):
        return self._lignes(self.debouches)

    def materiel_list(self):
        return self._lignes(self.materiel_fourni)

    def clean(self):
        if self.actif and not self.image:
            raise ValidationError({'actif': "Ajoutez une image avant de publier la formation."})


class FormationSessionPassee(models.Model):
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='sessions_passees')
    titre = models.CharField(max_length=160, blank=True, help_text="Ex. « Session Avril 2025 »")
    periode = models.CharField(max_length=120, blank=True, help_text="Ex. « 12 au 16 avril 2025 » (sinon calculée depuis les dates)")
    date_debut = models.DateField(blank=True, null=True)
    date_fin = models.DateField(blank=True, null=True)
    resume = models.TextField(blank=True, help_text="Quelques lignes : ce qui a été réalisé, nombre de participants…")
    lien_video = models.URLField(
        "Lien vidéo (YouTube ou TikTok)", max_length=500, blank=True,
        help_text="Vidéo de la session (ex. https://youtu.be/…). L'aperçu s'affiche automatiquement sur la page de la formation.",
    )
    ordre = models.PositiveSmallIntegerField(default=0)
    publiee = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_debut', '-date_fin', 'ordre', '-created_at']
        verbose_name = "Session passée"
        verbose_name_plural = "Sessions passées"

    def __str__(self):
        if self.titre:
            return f"{self.formation.titre} - {self.titre}"
        return f"{self.formation.titre} - Session {self.pk}"

    def get_periode_affichage(self):
        if self.periode:
            return self.periode
        if self.date_debut and self.date_fin:
            if self.date_debut == self.date_fin:
                return self.date_debut.strftime('%d/%m/%Y')
            return f"{self.date_debut.strftime('%d/%m/%Y')} au {self.date_fin.strftime('%d/%m/%Y')}"
        if self.date_debut:
            return self.date_debut.strftime('%d/%m/%Y')
        return ""

    def clean(self):
        self.lien_video = normaliser_lien_video(self.lien_video)
        valider_lien_video(self.lien_video)

    @property
    def video(self):
        return analyser(self.lien_video)


class Inscription(models.Model):
    MODE_PREFERENCE_CHOICES = [
        ('presentiel', 'Présentiel'),
        ('en_ligne', 'En ligne'),
    ]
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
    adresse = models.CharField(max_length=255, blank=True)
    mode_preference = models.CharField(
        max_length=20,
        choices=MODE_PREFERENCE_CHOICES,
        default='presentiel',
    )
    niveau_actuel = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    # Paiement frais inscription (2000 FCFA)
    fedapay_frais_id = models.CharField(max_length=100, blank=True)
    frais_payes_le = models.DateTimeField(null=True, blank=True)
    # Paiement formation
    fedapay_formation_id = models.CharField(max_length=100, blank=True)
    formation_payee_le = models.DateTimeField(null=True, blank=True)
    jitsi_room_name = models.CharField(max_length=120, blank=True)
    jitsi_room_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Inscription"

    def __str__(self):
        return f"{self.prenom} {self.nom} — {self.formation.titre}"

    def montant_inscription(self):
        from django.conf import settings
        return settings.KCOMAT_INFO['frais_inscription']

    def get_jitsi_room_url(self):
        if not self.jitsi_room_name:
            return ''
        from django.conf import settings
        base_url = (getattr(settings, 'JITSI_BASE_URL', '') or '').rstrip('/')
        if not base_url:
            return ''
        return f"{base_url}/{self.jitsi_room_name}"


class PaiementFormation(Inscription):
    class Meta:
        proxy = True
        ordering = ['-formation_payee_le', '-frais_payes_le', '-created_at']
        verbose_name = "Paiement formation"
        verbose_name_plural = "Paiements formation"
