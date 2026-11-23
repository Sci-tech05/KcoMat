from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import ACCOMPAGNEMENT_SLUG, Service, DemandeService


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['titre', 'icone', 'ordre', 'actif']
    list_editable = ['ordre', 'actif']
    prepopulated_fields = {'slug': ('titre',)}


class ConsultationFilter(admin.SimpleListFilter):
    title = "consultation (accompagnement)"
    parameter_name = 'consultation'

    def lookups(self, request, model_admin):
        return [('payee', 'Payée'), ('attente', 'Non payée (demande non soumise)')]

    def queryset(self, request, queryset):
        accompagnement = queryset.filter(service__slug=ACCOMPAGNEMENT_SLUG)
        if self.value() == 'payee':
            return accompagnement.filter(consultation_payee_le__isnull=False)
        if self.value() == 'attente':
            return accompagnement.filter(consultation_payee_le__isnull=True)
        # par défaut : une demande d'accompagnement n'est soumise qu'une fois la consultation payée
        return queryset.exclude(service__slug=ACCOMPAGNEMENT_SLUG, consultation_payee_le__isnull=True)


@admin.register(DemandeService)
class DemandeServiceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'email', 'service', 'intitule_projet', 'localite', 'consultation', 'traite', 'created_at']
    list_filter = ['traite', ConsultationFilter, 'service']
    list_editable = ['traite']
    list_select_related = ['service']
    search_fields = ['nom', 'email', 'intitule_projet', 'structure']
    date_hierarchy = 'created_at'
    readonly_fields = ['fedapay_consultation_id', 'facture', 'created_at']

    @admin.display(description='Consultation', ordering='consultation_payee_le')
    def consultation(self, obj):
        if not obj.service or obj.service.slug != ACCOMPAGNEMENT_SLUG:
            return '—'
        if obj.consultation_payee:
            return format_html('<span style="color:#047857;font-weight:700">Payée</span> '
                               '<span style="color:#64748B;font-size:.8rem">{}</span>',
                               obj.consultation_payee_le.strftime('%d/%m/%Y'))
        return format_html('<span style="color:#B45309;font-weight:700">En attente</span>')

    @admin.display(description='Facture')
    def facture(self, obj):
        if not obj.pk or not obj.service or obj.service.slug != ACCOMPAGNEMENT_SLUG:
            return '—'
        return format_html('<a href="{}" target="_blank">Facture de consultation (PDF)</a>',
                           reverse('services:facture_consultation', args=[obj.pk]))
