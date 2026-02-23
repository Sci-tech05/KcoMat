from django.contrib import admin
from .models import CategorieFormation, Formation, Inscription


@admin.register(CategorieFormation)
class CategorieFormationAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'couleur']
    prepopulated_fields = {'slug': ('nom',)}


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ['titre', 'categorie', 'prix', 'places_disponibles', 'actif', 'en_vedette', 'nouveau']
    list_filter = ['actif', 'en_vedette', 'nouveau', 'categorie', 'niveau']
    list_editable = ['actif', 'en_vedette', 'nouveau']
    search_fields = ['titre', 'description']
    prepopulated_fields = {'slug': ('titre',)}
    fieldsets = (
        ('Informations principales', {
            'fields': ('titre', 'slug', 'categorie', 'description_courte', 'description', 'image')
        }),
        ('Détails', {
            'fields': ('duree', 'niveau', 'prix', 'prix_avec_base', 'places_disponibles')
        }),
        ('Contenu pédagogique', {
            'fields': ('objectifs', 'prerequis')
        }),
        ('Statut et mise en avant', {
            'fields': ('actif', 'nouveau', 'en_vedette')
        }),
    )


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ['prenom', 'nom', 'email', 'formation', 'statut', 'created_at']
    list_filter = ['statut', 'formation']
    search_fields = ['nom', 'prenom', 'email', 'telephone']
    readonly_fields = ['created_at', 'frais_payes_le', 'formation_payee_le']
    date_hierarchy = 'created_at'
    list_select_related = ['formation']
