from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.text import slugify


class CategorieProduit(models.Model):
    nom = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icone = models.CharField(max_length=50, default='chip')
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = "Catégorie produit"
        verbose_name_plural = "Catégories produits"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


# Visuel affiché tant qu'un produit n'a pas de photo : couleur + icône (partials/icon.html) par catégorie
VISUELS_CATEGORIE = {
    'electronique': ('#2563EB', 'cpu'),
    'electricite': ('#D97706', 'zap'),
    'capteurs': ('#059669', 'target'),
    'moteurs-robotique': ('#7C3AED', 'bot'),
    'leds-afficheurs': ('#DB2777', 'sun'),
    'boutons-interrupteurs': ('#0891B2', 'grid'),
    'relais': ('#EA580C', 'network'),
    'resistances': ('#4D7C0F', 'chart'),
    'sans-fil': ('#4F46E5', 'wifi'),
    'gsm-gps': ('#0F766E', 'map-pin'),
    'labo': ('#9F1239', 'wrench'),
}
VISUEL_PAR_DEFAUT = ('#475569', 'cpu')


class Produit(models.Model):
    categorie = models.ForeignKey(CategorieProduit, on_delete=models.SET_NULL, null=True, related_name='produits')
    nom = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    description_courte = models.CharField(max_length=300)
    description = models.TextField()
    image = models.ImageField(upload_to='produits/', blank=True, null=True)
    prix = models.DecimalField(max_digits=10, decimal_places=0)
    stock = models.PositiveIntegerField(default=0)
    actif = models.BooleanField(default=True)
    nouveau = models.BooleanField(default=False)
    en_vedette = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nom']
        verbose_name = "Produit"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom

    @property
    def en_stock(self):
        return self.stock > 0

    @property
    def visuel(self):
        """Couleur, icône et libellé du visuel généré (produit sans photo)."""
        couleur, icone = VISUELS_CATEGORIE.get(self.categorie.slug if self.categorie else '', VISUEL_PAR_DEFAUT)
        return {'couleur': couleur, 'icone': icone,
                'libelle': self.reference or (self.categorie.nom if self.categorie else 'KcoMat')}


class ImageProduit(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='produits/gallery/')
    alt = models.CharField(max_length=200, blank=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre']


class Panier(models.Model):
    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Panier"

    def __str__(self):
        return f"Panier #{self.pk}"

    def total(self):
        return sum(item.sous_total() for item in self.items.all())

    def nombre_articles(self):
        return sum(item.quantite for item in self.items.all())


class PanierItem(models.Model):
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name='items')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)

    def sous_total(self):
        return self.produit.prix * self.quantite

    def __str__(self):
        return f"{self.quantite}x {self.produit.nom}"


class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de paiement'),
        ('payee', 'Payée'),
        ('en_preparation', 'En préparation'),
        ('expediee', 'Expédiée'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    adresse_livraison = models.TextField()
    ville = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    montant_total = models.DecimalField(max_digits=12, decimal_places=0)
    fedapay_transaction_id = models.CharField(max_length=100, blank=True)
    payee_le = models.DateTimeField(null=True, blank=True)
    # Suivi visible par le client : dates remplies automatiquement au changement de statut
    preparee_le = models.DateTimeField('Mise en préparation le', null=True, blank=True)
    expediee_le = models.DateTimeField('Expédiée le', null=True, blank=True)
    livree_le = models.DateTimeField('Livrée le', null=True, blank=True)
    annulee_le = models.DateTimeField('Annulée le', null=True, blank=True)
    message_suivi = models.CharField(
        'Message au client', max_length=300, blank=True,
        help_text="Affiché sur la page de suivi et dans l'e-mail (transporteur, n° de colis, créneau de livraison…).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # statut -> champ date rempli la première fois que la commande atteint ce statut
    DATES_STATUT = {
        'payee': 'payee_le',
        'en_preparation': 'preparee_le',
        'expediee': 'expediee_le',
        'livree': 'livree_le',
        'annulee': 'annulee_le',
    }
    ETAPES_SUIVI = ['payee', 'en_preparation', 'expediee', 'livree']

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Commande"

    def __str__(self):
        return f"Commande #{self.pk} — {self.prenom} {self.nom}"

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._statut_initial = instance.__dict__.get('statut')
        return instance

    @property
    def statut_a_change(self):
        return getattr(self, '_statut_initial', None) != self.statut

    def save(self, *args, **kwargs):
        champ = self.DATES_STATUT.get(self.statut)
        if champ and getattr(self, champ) is None:
            setattr(self, champ, timezone.now())
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = list(set(kwargs['update_fields']) | {champ})
        super().save(*args, **kwargs)

    def etapes_suivi(self):
        """Frise de suivi : [{code, libelle, date, faite, actuelle}] (vide si annulée ou non payée)."""
        if self.statut not in self.ETAPES_SUIVI:
            return []
        libelles = dict(self.STATUT_CHOICES)
        libelles['payee'] = 'Paiement reçu'
        rang = self.ETAPES_SUIVI.index(self.statut)
        return [
            {
                'code': code,
                'libelle': libelles[code],
                'date': getattr(self, self.DATES_STATUT[code]),
                'faite': i <= rang,
                'actuelle': i == rang,
                'trait_fait': i < rang,   # trait vers l'étape suivante en couleur
            }
            for i, code in enumerate(self.ETAPES_SUIVI)
        ]

    @property
    def progression(self):
        """Avancement en % pour la barre du tableau de bord."""
        if self.statut not in self.ETAPES_SUIVI:
            return 0
        return round(100 * self.ETAPES_SUIVI.index(self.statut) / (len(self.ETAPES_SUIVI) - 1))


class CommandeItem(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='items')
    produit = models.ForeignKey(Produit, on_delete=models.SET_NULL, null=True)
    nom_produit = models.CharField(max_length=200)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=0)
    quantite = models.PositiveIntegerField()

    def sous_total(self):
        return self.prix_unitaire * self.quantite
