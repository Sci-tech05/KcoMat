from django.db import models


class CategorieProjet(models.Model):
    nom = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class Projet(models.Model):
    titre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    categorie = models.ForeignKey(CategorieProjet, on_delete=models.SET_NULL, null=True, related_name='projets')
    description_courte = models.CharField(max_length=300)
    description = models.TextField()
    image_principale = models.ImageField(upload_to='projets/', blank=True, null=True)
    video_principale = models.FileField(
        upload_to='projets/videos/',
        blank=True, null=True,
        help_text="Vidéo de présentation du projet (MP4, WebM…)"
    )
    video_url = models.URLField(
        blank=True,
        help_text="Lien YouTube / Vimeo à intégrer (alternative à l'upload)"
    )
    client = models.CharField(max_length=200, blank=True)
    localite = models.CharField(max_length=200, blank=True)
    date_realisation = models.DateField(null=True, blank=True)
    technologies = models.CharField(max_length=300, blank=True, help_text="Ex: Arduino, Raspberry Pi, Zigbee")
    en_vedette = models.BooleanField(default=False)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Projet"

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre

    def get_technologies_list(self):
        return [t.strip() for t in self.technologies.split(',') if t.strip()]


class ImageProjet(models.Model):
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='projets/gallery/')
    legende = models.CharField(max_length=200, blank=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre']


class VideoProjet(models.Model):
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='videos')
    fichier = models.FileField(
        upload_to='projets/videos/',
        blank=True, null=True,
        help_text="Fichier vidéo (MP4, WebM…)"
    )
    url = models.URLField(
        blank=True,
        help_text="Lien YouTube / Vimeo à intégrer"
    )
    legende = models.CharField(max_length=200, blank=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre']
        verbose_name = "Vidéo du projet"
        verbose_name_plural = "Vidéos du projet"

    def __str__(self):
        return self.legende or f"Vidéo #{self.pk}"
