from django.db import models


class Service(models.Model):
    titre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description_courte = models.CharField(max_length=300)
    description = models.TextField()
    icone = models.CharField(max_length=50, default='bolt', help_text="Nom icône HeroIcons")
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    couleur = models.CharField(max_length=30, default='blue')
    ordre = models.PositiveSmallIntegerField(default=0)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordre']
        verbose_name = "Service"

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre


class DemandeService(models.Model):
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, related_name='demandes')
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    localite = models.CharField(max_length=200)
    description_besoin = models.TextField()
    budget_estime = models.CharField(max_length=100, blank=True)
    traite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande de service"
        verbose_name_plural = "Demandes de service"

    def __str__(self):
        return f"{self.nom} — {self.service}"
