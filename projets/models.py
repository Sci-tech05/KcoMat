from django.core.exceptions import ValidationError
from django.db import models

from core.video import analyser, normaliser_lien_video, valider_lien_video


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
    lien_video = models.URLField(
        "Lien vidéo principale (YouTube ou TikTok)", max_length=500, blank=True,
        help_text="Soit un lien vidéo, soit une image principale (pas les deux). "
                  "Ex. https://www.youtube.com/watch?v=… ou https://www.tiktok.com/@kcomat3/video/…",
    )
    image = models.ImageField(
        "Image principale", upload_to='projets/', blank=True, null=True,
        help_text="Uniquement si le projet n'a pas de vidéo principale. Format paysage conseillé (1600 × 900 px).",
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

    def clean(self):
        self.lien_video = normaliser_lien_video(self.lien_video)
        valider_lien_video(self.lien_video)
        if self.lien_video and self.image:
            raise ValidationError(
                "Un projet a soit une vidéo principale, soit une image principale, pas les deux : "
                "videz le lien vidéo ou retirez l'image. Les autres vidéos s'ajoutent dans « Vidéos supplémentaires ».")
        if self.actif and not (self.lien_video or self.image):
            raise ValidationError("Ajoutez une vidéo principale (lien YouTube ou TikTok) ou une image principale pour publier le projet.")

    @property
    def video(self):
        return analyser(self.lien_video)

    @property
    def miniature(self):
        if self.image:
            return self.image.url
        video = self.video
        return video.miniature if video else ''


class VideoProjet(models.Model):
    """Vidéos supplémentaires (galerie) : liens YouTube / TikTok uniquement."""
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='videos')
    url = models.URLField("Lien vidéo (YouTube ou TikTok)", max_length=500)
    legende = models.CharField("Légende", max_length=200, blank=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre']
        verbose_name = "Vidéo supplémentaire"
        verbose_name_plural = "Vidéos supplémentaires"

    def __str__(self):
        return self.legende or f"Vidéo #{self.pk}"

    def clean(self):
        self.url = normaliser_lien_video(self.url)
        valider_lien_video(self.url)

    @property
    def video(self):
        return analyser(self.url)
