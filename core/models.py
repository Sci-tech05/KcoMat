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
