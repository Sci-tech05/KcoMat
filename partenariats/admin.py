from django.contrib import admin
from .models import Partenaire, DemandePartenariat


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_partenaire', 'site_web', 'actif', 'ordre']
    list_editable = ['actif', 'ordre']
    list_filter = ['type_partenaire', 'actif']


@admin.register(DemandePartenariat)
class DemandePartenariatAdmin(admin.ModelAdmin):
    list_display = ['nom_organisation', 'nom_contact', 'email', 'traite', 'created_at']
    list_filter = ['traite']
    list_editable = ['traite']
    search_fields = ['nom_organisation', 'nom_contact', 'email']
    date_hierarchy = 'created_at'
