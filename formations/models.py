from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.exceptions import ValidationError


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


class FormationSessionPassee(models.Model):
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='sessions_passees')
    titre = models.CharField(max_length=160, blank=True, help_text="Ex: Session Aout 2025")
    periode = models.CharField(max_length=120, blank=True, help_text="Ex: 12 au 16 aout 2025")
    date_debut = models.DateField(blank=True, null=True)
    date_fin = models.DateField(blank=True, null=True)
    resume = models.TextField(blank=True, help_text="Description breve de la session passee")
    image_couverture = models.ImageField(
        upload_to='formations/sessions/covers/',
        blank=True,
        null=True,
        help_text="Image principale de la session passee.",
    )
    video_apercu_file = models.FileField(
        upload_to='formations/sessions/covers/videos/',
        blank=True,
        null=True,
        help_text="Video principale (fichier).",
    )
    video_apercu_url = models.URLField(
        blank=True,
        help_text="Lien YouTube/Vimeo de la video principale (optionnel).",
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
        return "Periode non precisee"

    def get_video_apercu_embed_url(self):
        url = (self.video_apercu_url or '').strip()
        if not url:
            return ''
        if 'youtube.com/watch?v=' in url:
            video_id = url.split('watch?v=')[-1].split('&')[0]
            return f'https://www.youtube.com/embed/{video_id}'
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[-1].split('?')[0]
            return f'https://www.youtube.com/embed/{video_id}'
        if 'vimeo.com/' in url:
            video_id = url.rstrip('/').split('/')[-1]
            return f'https://player.vimeo.com/video/{video_id}'
        return url


class FormationSessionMedia(models.Model):
    TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    session = models.ForeignKey(FormationSessionPassee, on_delete=models.CASCADE, related_name='medias')
    type_media = models.CharField(max_length=10, choices=TYPE_CHOICES, default='image')
    image = models.ImageField(upload_to='formations/sessions/images/', blank=True, null=True)
    video_file = models.FileField(upload_to='formations/sessions/videos/', blank=True, null=True)
    video_url = models.URLField(blank=True, help_text="Lien YouTube/Vimeo (optionnel)")
    legende = models.CharField(max_length=180, blank=True)
    ordre = models.PositiveSmallIntegerField(default=0)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre', 'id']
        verbose_name = "Média de session"
        verbose_name_plural = "Médias de session"

    def __str__(self):
        label = self.legende or self.get_type_media_display()
        return f"{self.session} - {label}"

    def clean(self):
        if self.type_media == 'image' and not self.image:
            raise ValidationError("Ajoutez une image pour un media de type image.")
        if self.type_media == 'video' and not self.video_file and not self.video_url:
            raise ValidationError("Ajoutez un fichier video ou une URL video pour un media de type video.")

    def get_video_embed_url(self):
        url = (self.video_url or '').strip()
        if not url:
            return ''
        if 'youtube.com/watch?v=' in url:
            video_id = url.split('watch?v=')[-1].split('&')[0]
            return f'https://www.youtube.com/embed/{video_id}'
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[-1].split('?')[0]
            return f'https://www.youtube.com/embed/{video_id}'
        if 'vimeo.com/' in url:
            video_id = url.rstrip('/').split('/')[-1]
            return f'https://player.vimeo.com/video/{video_id}'
        return url


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
