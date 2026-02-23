from django.contrib import admin
from .models import CategorieProduit, Produit, ImageProduit, Commande, CommandeItem


@admin.register(CategorieProduit)
class CategorieProduitAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'ordre']
    list_editable = ['ordre']
    prepopulated_fields = {'slug': ('nom',)}


class ImageProduitInline(admin.TabularInline):
    model = ImageProduit
    extra = 2
    fields = ['image', 'alt', 'ordre']


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ['nom', 'categorie', 'prix', 'stock', 'actif', 'en_vedette', 'nouveau']
    list_filter = ['actif', 'en_vedette', 'nouveau', 'categorie']
    list_editable = ['actif', 'en_vedette', 'prix', 'stock']
    search_fields = ['nom', 'reference', 'description']
    prepopulated_fields = {'slug': ('nom',)}
    inlines = [ImageProduitInline]


class CommandeItemInline(admin.TabularInline):
    model = CommandeItem
    extra = 0
    readonly_fields = ['produit', 'nom_produit', 'prix_unitaire', 'quantite']


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'prenom', 'montant_total', 'statut', 'created_at']
    list_filter = ['statut']
    search_fields = ['nom', 'prenom', 'email', 'telephone']
    readonly_fields = ['created_at', 'payee_le', 'fedapay_transaction_id']
    inlines = [CommandeItemInline]
    date_hierarchy = 'created_at'
