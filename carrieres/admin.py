from django.contrib import admin
from .models import Offre, Candidature


@admin.register(Offre)
class OffreAdmin(admin.ModelAdmin):
    list_display = ['titre', 'type_offre', 'domaine', 'localite', 'date_limite', 'actif']
    list_filter = ['type_offre', 'actif']
    list_editable = ['actif']
    search_fields = ['titre', 'domaine']
    prepopulated_fields = {'slug': ('titre',)}


@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    list_display = ['prenom', 'nom', 'email', 'offre', 'traite', 'created_at']
    list_filter = ['traite', 'offre']
    list_editable = ['traite']
    search_fields = ['nom', 'prenom', 'email']
    date_hierarchy = 'created_at'
