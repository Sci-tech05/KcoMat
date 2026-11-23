from django.db import models

# Service à procédure propre (consultation payante → matériels → réalisation sur devis)
ACCOMPAGNEMENT_SLUG = 'accompagnement-de-projet'
FRAIS_CONSULTATION = 2000


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

    @property
    def est_accompagnement(self):
        return self.slug == ACCOMPAGNEMENT_SLUG


class DemandeService(models.Model):
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, related_name='demandes')
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    localite = models.CharField(max_length=200)
    structure = models.CharField("Établissement / structure", max_length=200, blank=True)
    intitule_projet = models.CharField("Intitulé du projet", max_length=200, blank=True)
    description_besoin = models.TextField()
    budget_estime = models.CharField(max_length=100, blank=True)
    traite = models.BooleanField(default=False)
    # Accompagnement de projet : frais de consultation réglés en ligne (FedaPay)
    fedapay_consultation_id = models.CharField("Transaction FedaPay", max_length=100, blank=True, editable=False)
    consultation_payee_le = models.DateTimeField("Consultation payée le", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande de service"
        verbose_name_plural = "Demandes de service"

    def __str__(self):
        return f"{self.nom} — {self.service}"

    @property
    def consultation_payee(self):
        return self.consultation_payee_le is not None

    @property
    def numero_facture(self):
        return f"ACC-CONS-{self.pk:06d}"
