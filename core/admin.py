from django.contrib import admin
from .models import TeamMember, Temoignage, Statistique, ContactMessage


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['nom', 'poste', 'ordre']
    list_editable = ['ordre']
    search_fields = ['nom', 'poste']


@admin.register(Temoignage)
class TemoignageAdmin(admin.ModelAdmin):
    list_display = ['nom', 'poste', 'note', 'actif', 'created_at']
    list_filter = ['actif', 'note']
    list_editable = ['actif']
    search_fields = ['nom']


@admin.register(Statistique)
class StatistiqueAdmin(admin.ModelAdmin):
    list_display = ['libelle', 'valeur', 'icone', 'ordre']
    list_editable = ['ordre']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['nom', 'email', 'sujet', 'lu', 'created_at']
    list_filter = ['lu']
    list_editable = ['lu']
    search_fields = ['nom', 'email', 'sujet']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
