from django.contrib import admin
from .models import Projet, CategorieProjet, ImageProjet, VideoProjet


@admin.register(CategorieProjet)
class CategorieProjetAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug']
    prepopulated_fields = {'slug': ('nom',)}


class ImageProjetInline(admin.TabularInline):
    model = ImageProjet
    extra = 2
    fields = ['image', 'legende', 'ordre']


class VideoProjetInline(admin.TabularInline):
    model = VideoProjet
    extra = 1
    fields = ['fichier', 'url', 'legende', 'ordre']
    verbose_name = "Vidéo (galerie)"
    verbose_name_plural = "Vidéos (galerie)"


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display = ['titre', 'categorie', 'client', 'date_realisation', 'en_vedette', 'actif']
    list_filter = ['actif', 'en_vedette', 'categorie']
    list_editable = ['actif', 'en_vedette']
    search_fields = ['titre', 'client', 'description']
    prepopulated_fields = {'slug': ('titre',)}
    fieldsets = (
        ('Informations générales', {
            'fields': ('titre', 'slug', 'categorie', 'description_courte', 'description'),
        }),
        ('Média principal', {
            'description': 'Ajoutez une image OU une vidéo principale (ou les deux).',
            'fields': ('image_principale', 'video_principale', 'video_url'),
        }),
        ('Détails', {
            'fields': ('client', 'localite', 'date_realisation', 'technologies'),
        }),
        ('Visibilité', {
            'fields': ('en_vedette', 'actif'),
        }),
    )
    inlines = [ImageProjetInline, VideoProjetInline]
