from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Avis, TeamMember, Temoignage, Statistique, ContactMessage


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


@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    list_display = ['etoiles', 'article', 'utilisateur', 'extrait', 'achat_verifie', 'publie', 'modifie_le']
    list_filter = ['publie', 'note', 'achat_verifie', 'content_type']
    list_editable = ['publie']
    search_fields = ['commentaire', 'utilisateur__username', 'utilisateur__first_name', 'utilisateur__email']
    readonly_fields = ['content_type', 'object_id', 'utilisateur', 'note', 'commentaire', 'achat_verifie', 'cree_le', 'modifie_le']
    fields = ['publie', 'note', 'commentaire', 'utilisateur', 'achat_verifie', 'content_type', 'object_id', 'cree_le', 'modifie_le']
    date_hierarchy = 'cree_le'
    actions = ['publier', 'masquer']
    list_select_related = ['utilisateur', 'content_type']

    def has_add_permission(self, request):
        return False  # les avis viennent uniquement des clients

    @admin.display(description='Note', ordering='note')
    def etoiles(self, obj):
        return format_html('<span style="color:#F59E0B;letter-spacing:1px">{}</span><span style="color:#CBD5E1">{}</span>', '★' * obj.note, '★' * (5 - obj.note))

    @admin.display(description='Article')
    def article(self, obj):
        page = {'produit': 'boutique:detail', 'formation': 'formations:detail'}.get(obj.content_type.model)
        if page and obj.objet is not None:
            return format_html('<a href="{}#avis" target="_blank">{}</a>', reverse(page, args=[obj.objet.slug]), obj.objet)
        return obj.objet

    @admin.display(description='Commentaire')
    def extrait(self, obj):
        return (obj.commentaire[:80] + '…') if len(obj.commentaire) > 80 else obj.commentaire

    @admin.action(description='Publier les avis sélectionnés')
    def publier(self, request, queryset):
        self.message_user(request, f'{queryset.update(publie=True)} avis publié(s).')

    @admin.action(description='Masquer les avis sélectionnés')
    def masquer(self, request, queryset):
        self.message_user(request, f'{queryset.update(publie=False)} avis masqué(s).')
