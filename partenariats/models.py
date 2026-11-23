from pathlib import Path

from django.core.files.base import ContentFile
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
    logo = models.ImageField(upload_to='partenaires/demandes/', blank=True, null=True)
    traite = models.BooleanField("Traitée", default=False,
                                 help_text="Cochée : l'organisation apparaît aussitôt parmi les partenaires du site.")
    partenaire = models.OneToOneField(Partenaire, on_delete=models.SET_NULL, null=True, blank=True, editable=False,
                                      related_name='demande', verbose_name="Partenaire publié")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande de partenariat"
        verbose_name_plural = "Demandes de partenariat"

    def __str__(self):
        return f"{self.nom_organisation} — {self.nom_contact}"

    def save(self, *args, **kwargs):
        avant = DemandePartenariat.objects.filter(pk=self.pk).values_list('traite', flat=True).first() if self.pk else False
        super().save(*args, **kwargs)
        if self.traite and (not avant or self.partenaire_id is None):
            self.publier_partenaire()
        elif avant and not self.traite and self.partenaire_id:
            Partenaire.objects.filter(pk=self.partenaire_id).update(actif=False)

    def publier_partenaire(self):
        """Demande traitée → partenaire affiché sur le site (créé une seule fois, réactivé ensuite)."""
        if self.partenaire_id:
            Partenaire.objects.filter(pk=self.partenaire_id).update(actif=True)
            return self.partenaire
        partenaire = Partenaire(nom=self.nom_organisation, site_web=self.site_web, actif=True,
                                type_partenaire=_type_partenaire(self.type_organisation))
        if self.logo:
            # copie indépendante : supprimer la demande ne doit pas effacer le logo publié
            # (fichier non encore écrit : la compression des logos s'applique à l'enregistrement)
            self.logo.open('rb')
            try:
                partenaire.logo = ContentFile(self.logo.read(), name=Path(self.logo.name).name)
            finally:
                self.logo.close()
        partenaire.save()
        DemandePartenariat.objects.filter(pk=self.pk).update(partenaire=partenaire)
        self.partenaire = partenaire
        return partenaire


def _type_partenaire(texte):
    texte = (texte or '').lower()
    if any(mot in texte for mot in ('ong', 'association')):
        return 'ong'
    if any(mot in texte for mot in ('institution', 'école', 'ecole', 'université', 'universite', 'ministère', 'mairie')):
        return 'institution'
    return 'entreprise'
