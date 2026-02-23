from django.contrib import admin
from .models import Service, DemandeService


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['titre', 'icone', 'ordre', 'actif']
    list_editable = ['ordre', 'actif']
    prepopulated_fields = {'slug': ('titre',)}


@admin.register(DemandeService)
class DemandeServiceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'email', 'service', 'localite', 'traite', 'created_at']
    list_filter = ['traite', 'service']
    list_editable = ['traite']
    search_fields = ['nom', 'email']
    date_hierarchy = 'created_at'
