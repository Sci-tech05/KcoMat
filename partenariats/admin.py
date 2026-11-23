from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .models import Partenaire, DemandePartenariat


def _logo(fichier):
    if not fichier:
        return '—'
    return format_html('<img src="{}" alt="" style="height:36px;max-width:90px;object-fit:contain;border-radius:6px;'
                       'background:#F8FAFC;padding:2px">', fichier.url)


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ['apercu_logo', 'nom', 'type_partenaire', 'site_web', 'actif', 'ordre']
    list_display_links = ['nom']
    list_editable = ['actif', 'ordre']
    list_filter = ['type_partenaire', 'actif']

    @admin.display(description='Logo')
    def apercu_logo(self, obj):
        return _logo(obj.logo)


@admin.register(DemandePartenariat)
class DemandePartenariatAdmin(admin.ModelAdmin):
    actions = ['accepter']
    list_display = ['apercu_logo', 'nom_organisation', 'nom_contact', 'email', 'traite', 'partenaire_publie', 'created_at']
    list_display_links = ['nom_organisation']
    list_filter = ['traite']
    list_editable = ['traite']
    search_fields = ['nom_organisation', 'nom_contact', 'email']
    date_hierarchy = 'created_at'
    readonly_fields = ['partenaire_publie', 'created_at']
    list_select_related = ['partenaire']

    @admin.display(description='Logo')
    def apercu_logo(self, obj):
        return _logo(obj.logo)

    @admin.display(description='Sur le site')
    def partenaire_publie(self, obj):
        if not obj.partenaire_id:
            return '—'
        lien = reverse('admin:partenariats_partenaire_change', args=[obj.partenaire_id])
        etat = 'Affiché' if obj.partenaire.actif else 'Masqué'
        return format_html('<a href="{}">{}</a>', lien, etat)

    @admin.action(description="Marquer comme traitées et afficher parmi les partenaires du site")
    def accepter(self, request, queryset):
        n = 0
        for demande in queryset:
            demande.traite = True
            demande.save()
            n += 1
        self.message_user(request, f"{n} organisation(s) affichée(s) parmi les partenaires du site.", messages.SUCCESS)
