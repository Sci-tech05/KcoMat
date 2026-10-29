import csv
from datetime import datetime

from django.contrib import admin, messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from notifications.admin import notifier_abonnes
from notifications.push import notifier_publication

from .attestation import reponse_pdf
from .catalogue import CATALOGUE, HEURE_DEBUT, HEURE_FIN, charger_catalogue
from .models import ParticipationWebinaire, Webinaire
from .rappels import envoyer_rappel

STATUTS = {
    'a_venir': ('À venir', '#1D4ED8', '#EFF6FF'),
    'ouvert': ('Salle ouverte', '#B45309', '#FFF7E6'),
    'en_direct': ('En direct', '#BE123C', '#FFF1F2'),
    'termine': ('Terminé', '#475569', '#F1F5F9'),
}


def _pastille(texte, couleur, fond):
    return format_html('<span style="display:inline-block;padding:.15rem .55rem;border-radius:999px;background:{};'
                       'color:{};font-size:.72rem;font-weight:700;white-space:nowrap">{}</span>', fond, couleur, texte)


class ParticipationInline(admin.TabularInline):
    model = ParticipationWebinaire
    extra = 0
    can_delete = True
    fields = ['prenom', 'nom', 'email', 'inscrit_le', 'rejoint_le', 'attestation']
    readonly_fields = ['inscrit_le', 'attestation']
    verbose_name_plural = "Participants inscrits"

    def has_add_permission(self, request, obj=None):
        return False   # les inscriptions se font depuis le site (compte obligatoire)

    @admin.display(description='Attestation')
    def attestation(self, obj):
        if not obj.pk or not obj.a_participe:
            return '—'
        return format_html('<a href="{}" target="_blank">PDF</a>',
                           reverse('admin:webinaires_participationwebinaire_attestation', args=[obj.pk]))


@admin.register(Webinaire)
class WebinaireAdmin(admin.ModelAdmin):
    change_list_template = 'admin/webinaires/webinaire/change_list.html'
    actions = ['publier', 'masquer', notifier_abonnes, 'mettre_horaire_soiree', 'envoyer_rappel_maintenant', 'exporter_participants']
    list_display = ['vignette', 'titre', 'quand', 'statut_badge', 'inscrits', 'presents', 'actif']
    list_display_links = ['titre']
    list_editable = ['actif']
    list_filter = ['actif', 'theme']
    search_fields = ['titre', 'accroche', 'intervenant']
    prepopulated_fields = {'slug': ('titre',)}
    date_hierarchy = 'date_debut'
    readonly_fields = ['salle_animateur', 'rappel_envoye_le']
    fieldsets = (
        ('Annonce', {
            'description': "Titre, image et description affichés sur l'accueil et la page Webinaires.",
            'fields': ('titre', 'slug', 'theme', 'image', 'accroche', 'description', 'points_cles'),
        }),
        ('Intervenant', {'fields': ('intervenant', 'intervenant_fonction')}),
        ('Date et heure (heure du Bénin)', {
            'description': "Rappel push + e-mail aux inscrits 20 min avant le début ; bouton « Participer » 10 min avant ; "
                           "attestations téléchargeables dès l'heure de fin.",
            'fields': (('date_debut', 'date_fin'), 'places'),
        }),
        ('Publication', {'fields': ('actif',)}),
        ('Séance en ligne', {
            'description': "Entrez dans la salle quelques minutes avant les participants : la première personne connectée "
                           "devient modératrice de la visioconférence.",
            'fields': ('salle_animateur', 'rappel_envoye_le'),
        }),
    )
    inlines = [ParticipationInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            n_inscrits=Count('participations', distinct=True),
            n_presents=Count('participations', filter=Q(participations__rejoint_le__isnull=False), distinct=True),
        )

    @admin.display(description='Image')
    def vignette(self, obj):
        if obj.image:
            return format_html('<img src="{}" alt="" style="width:64px;height:36px;object-fit:cover;border-radius:8px">', obj.image.url)
        return format_html('<span style="display:inline-block;width:64px;height:36px;border-radius:8px;'
                           'background:linear-gradient(135deg,var(--a),var(--b));{}"></span>', obj.theme_style.replace('--wb-', '--'))

    @admin.display(description='Date', ordering='date_debut')
    def quand(self, obj):
        debut, fin = timezone.localtime(obj.date_debut), timezone.localtime(obj.date_fin)
        return format_html('<b>{}</b><br><span style="color:#64748B;font-size:.8rem">{} → {}</span>',
                           debut.strftime('%d/%m/%Y'), debut.strftime('%H:%M'), fin.strftime('%H:%M'))

    @admin.display(description='Statut')
    def statut_badge(self, obj):
        return _pastille(*STATUTS[obj.statut()])

    @admin.display(description='Inscrits', ordering='n_inscrits')
    def inscrits(self, obj):
        return f"{obj.n_inscrits} / {obj.places}" if obj.places else obj.n_inscrits

    @admin.display(description='Présents', ordering='n_presents')
    def presents(self, obj):
        return obj.n_presents

    @admin.display(description="Salle (animateur)")
    def salle_animateur(self, obj):
        if not obj.pk:
            return "Enregistrez le webinaire pour créer la salle."
        return format_html('<a class="btn btn-sm btn-primary" href="{}" target="_blank">Entrer dans la salle</a>'
                           '<span style="margin-left:.6rem;color:#64748B">{}</span>',
                           reverse('webinaires:salle', args=[obj.slug]), obj.get_salle_url())

    @admin.action(description="Publier les webinaires sélectionnés (prévient les abonnés)")
    def publier(self, request, queryset):
        maintenant = timezone.now()
        ignores = queryset.filter(actif=False, date_fin__lte=maintenant).count()
        nouveaux = list(queryset.filter(actif=False, date_fin__gt=maintenant).values_list('pk', flat=True))
        n = Webinaire.objects.filter(pk__in=nouveaux).update(actif=True)
        for webinaire in Webinaire.objects.filter(pk__in=nouveaux):   # update() ne déclenche pas les signaux
            notifier_publication(webinaire)
        self.message_user(request, f"{n} webinaire(s) publié(s) ; les abonnés ont été prévenus."
                          + (f" {ignores} webinaire(s) déjà passé(s) ignoré(s)." if ignores else ""),
                          messages.SUCCESS if n else messages.WARNING)

    @admin.action(description="Masquer les webinaires sélectionnés")
    def masquer(self, request, queryset):
        self.message_user(request, f"{queryset.update(actif=False)} webinaire(s) masqué(s).", messages.SUCCESS)

    @admin.action(description=f"Programmer de {HEURE_DEBUT:%H} h à {HEURE_FIN:%H} h (même jour)")
    def mettre_horaire_soiree(self, request, queryset):
        zone = timezone.get_current_timezone()
        n = 0
        for webinaire in queryset.filter(date_fin__gt=timezone.now()):
            jour = timezone.localtime(webinaire.date_debut).date()
            webinaire.date_debut = timezone.make_aware(datetime.combine(jour, HEURE_DEBUT), zone)
            webinaire.date_fin = timezone.make_aware(datetime.combine(jour, HEURE_FIN), zone)
            webinaire.rappel_envoye_le = None
            webinaire.save(update_fields=['date_debut', 'date_fin', 'rappel_envoye_le', 'updated_at'])
            n += 1
        self.message_user(request, f"{n} webinaire(s) programmé(s) de {HEURE_DEBUT:%H} h à {HEURE_FIN:%H} h.", messages.SUCCESS)

    @admin.action(description="Envoyer le rappel maintenant (push + e-mail aux inscrits)")
    def envoyer_rappel_maintenant(self, request, queryset):
        total = 0
        for webinaire in queryset.filter(actif=True):
            total += envoyer_rappel(webinaire)
            Webinaire.objects.filter(pk=webinaire.pk).update(rappel_envoye_le=timezone.now())
        self.message_user(request, f"Rappel envoyé : {total} e-mail(s) aux inscrits, notification push aux abonnés.",
                          messages.SUCCESS)

    @admin.action(description="Exporter les participants (CSV)")
    def exporter_participants(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="participants-webinaires.csv"'
        response.write('﻿')   # Excel : accents corrects
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Webinaire', 'Date', 'Prénom', 'Nom', 'E-mail', 'Inscrit le', 'Présent', 'N° attestation'])
        participations = (ParticipationWebinaire.objects.filter(webinaire__in=queryset)
                          .select_related('webinaire').order_by('webinaire__date_debut', 'nom'))
        for p in participations:
            writer.writerow([p.webinaire.titre, timezone.localtime(p.webinaire.date_debut).strftime('%d/%m/%Y %H:%M'),
                             p.prenom, p.nom, p.email, timezone.localtime(p.inscrit_le).strftime('%d/%m/%Y %H:%M'),
                             'Oui' if p.a_participe else 'Non', p.numero_attestation if p.a_participe else ''])
        return response

    def get_urls(self):
        return [path('charger-catalogue/', self.admin_site.admin_view(self.charger_catalogue_view),
                     name='webinaires_webinaire_charger_catalogue')] + super().get_urls()

    def charger_catalogue_view(self, request):
        if request.method == 'POST':
            crees, _ = charger_catalogue()
            if crees:
                self.message_user(request, f"{crees} webinaire(s) ajouté(s), masqués : vérifiez la date, ajoutez une image "
                                           "puis publiez-les.", messages.SUCCESS)
            else:
                self.message_user(request, "Tous les webinaires proposés sont déjà présents.", messages.INFO)
        return redirect('admin:webinaires_webinaire_changelist')

    def changelist_view(self, request, extra_context=None):
        maintenant = timezone.now()
        qs = Webinaire.objects.all()
        extra_context = {
            **(extra_context or {}),
            'nb_a_venir': qs.filter(actif=True, date_fin__gt=maintenant).count(),
            'nb_masques': qs.filter(actif=False).count(),
            'nb_participants': ParticipationWebinaire.objects.count(),
            'catalogue_total': len(CATALOGUE),
        }
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ParticipationWebinaire)
class ParticipationWebinaireAdmin(admin.ModelAdmin):
    list_display = ['nom_complet', 'email', 'webinaire', 'inscrit_le', 'presence', 'lien_attestation']
    list_filter = ['webinaire', ('rejoint_le', admin.EmptyFieldListFilter)]
    search_fields = ['prenom', 'nom', 'email', 'code_verification', 'webinaire__titre']
    readonly_fields = ['webinaire', 'utilisateur', 'inscrit_le', 'code_verification']
    fields = ['webinaire', 'utilisateur', ('prenom', 'nom'), 'email', 'inscrit_le', 'rejoint_le', 'code_verification']
    actions = ['marquer_present']

    def has_add_permission(self, request):
        return False

    @admin.display(description='Participant', ordering='nom')
    def nom_complet(self, obj):
        return obj.nom_complet

    @admin.display(description='Présence', ordering='rejoint_le')
    def presence(self, obj):
        if obj.a_participe:
            return _pastille(f"Présent · {timezone.localtime(obj.rejoint_le):%H:%M}", '#047857', '#ECFDF5')
        return _pastille('Absent', '#64748B', '#F1F5F9')

    @admin.display(description='Attestation')
    def lien_attestation(self, obj):
        if not obj.a_participe:
            return '—'
        return format_html('<a href="{}" target="_blank">{}</a>',
                           reverse('admin:webinaires_participationwebinaire_attestation', args=[obj.pk]), obj.numero_attestation)

    @admin.action(description="Marquer présent (ouvre le droit à l'attestation)")
    def marquer_present(self, request, queryset):
        n = queryset.filter(rejoint_le__isnull=True).update(rejoint_le=timezone.now())
        self.message_user(request, f"{n} participant(s) marqué(s) présent(s).", messages.SUCCESS)

    def get_urls(self):
        return [path('<int:pk>/attestation.pdf', self.admin_site.admin_view(self.attestation_view),
                     name='webinaires_participationwebinaire_attestation')] + super().get_urls()

    def attestation_view(self, request, pk):
        participation = get_object_or_404(ParticipationWebinaire.objects.select_related('webinaire'), pk=pk)
        return reponse_pdf(participation, telechargement=False)
