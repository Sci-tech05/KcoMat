from django.db import models
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Commande"

    def __str__(self):
        return f"Commande #{self.pk} — {self.prenom} {self.nom}"


class CommandeItem(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='items')
    produit = models.ForeignKey(Produit, on_delete=models.SET_NULL, null=True)
    nom_produit = models.CharField(max_length=200)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=0)
    quantite = models.PositiveIntegerField()

    def sous_total(self):
        return self.prix_unitaire * self.quantite
