from django.contrib import admin
from django.utils.html import format_html

from notifications.admin import notifier_abonnes

from .models import CategorieProjet, Projet, VideoProjet


def apercu_video(video, largeur=220):
    """Miniature cliquable (YouTube) ou pastille TikTok, pour l'admin."""
    if video is None:
        return format_html('<span style="color:#94A3B8">Aucune vidéo</span>')
    if video.miniature:
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" title="Ouvrir sur {}" style="position:relative;display:inline-block">'
            '<img src="{}" alt="" style="width:{}px;aspect-ratio:16/9;object-fit:cover;border-radius:10px;border:1px solid #E5E9F2">'
            '<span style="position:absolute;inset:0;display:grid;place-items:center;color:#fff;font-size:1.6rem;'
            'text-shadow:0 2px 8px rgba(0,0,0,.6)">▶</span></a>',
            video.lien_plateforme, video.nom_plateforme, video.miniature, largeur)
    return format_html(
        '<a href="{}" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:.4rem;padding:.4rem .75rem;'
        'border-radius:10px;background:#0F172A;color:#fff;font-weight:700;font-size:.8rem">♪ Vidéo TikTok</a>',
        video.lien_plateforme)


@admin.register(CategorieProjet)
class CategorieProjetAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug']
    prepopulated_fields = {'slug': ('nom',)}


class VideoProjetInline(admin.TabularInline):
    model = VideoProjet
    extra = 1
    fields = ['url', 'legende', 'ordre', 'apercu']
    readonly_fields = ['apercu']

    @admin.display(description='Aperçu')
    def apercu(self, obj):
        return apercu_video(obj.video, 140) if obj.pk else '—'


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    actions = [notifier_abonnes]
    list_display = ['miniature_liste', 'titre', 'categorie', 'client', 'date_realisation', 'en_vedette', 'actif']
    list_display_links = ['titre']
    list_filter = ['actif', 'en_vedette', 'categorie']
    list_editable = ['actif', 'en_vedette']
    search_fields = ['titre', 'client', 'description']
    prepopulated_fields = {'slug': ('titre',)}
    readonly_fields = ['apercu']
    fieldsets = (
        ('Informations générales', {
            'fields': ('titre', 'slug', 'categorie', 'description_courte', 'description'),
        }),
        ('Vidéo du projet', {
            'description': "Collez simplement le lien d'une vidéo YouTube ou TikTok : l'aperçu et le lecteur s'affichent "
                           "automatiquement sur le site. Aucune image ni fichier à téléverser.",
            'fields': ('lien_video', 'apercu'),
        }),
        ('Détails', {
            'fields': ('client', 'localite', 'date_realisation', 'technologies'),
        }),
        ('Visibilité', {
            'fields': ('en_vedette', 'actif'),
        }),
    )
    inlines = [VideoProjetInline]

    @admin.display(description='Vidéo')
    def miniature_liste(self, obj):
        return apercu_video(obj.video, 120)

    @admin.display(description='Aperçu actuel')
    def apercu(self, obj):
        return apercu_video(obj.video, 320) if obj.pk else "Enregistrez pour voir l'aperçu."
