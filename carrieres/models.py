from django.db import models


class Offre(models.Model):
    TYPE_CHOICES = [
        ('emploi', 'Emploi'),
        ('stage', 'Stage'),
        ('freelance', 'Freelance'),
    ]
    titre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    type_offre = models.CharField(max_length=20, choices=TYPE_CHOICES, default='emploi')
    domaine = models.CharField(max_length=150)
    description = models.TextField()
    competences_requises = models.TextField()
    localite = models.CharField(max_length=100, default='Lokossa, Bénin')
    remuneration = models.CharField(max_length=100, blank=True)
    date_limite = models.DateField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Offre"

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.get_type_offre_display()}] {self.titre}"


class Candidature(models.Model):
    offre = models.ForeignKey(Offre, on_delete=models.CASCADE, related_name='candidatures')
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    cv = models.FileField(upload_to='cv/')
    lettre_motivation = models.FileField(upload_to='lettres_motivation/', blank=True, null=True)
    traite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Candidature"

    def __str__(self):
        return f"{self.prenom} {self.nom} → {self.offre.titre}"
