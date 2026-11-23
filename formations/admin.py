from django.contrib import admin
from notifications.admin import notifier_abonnes
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from django import forms
from django.contrib import messages
from django.contrib.admin import helpers
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse

from notifications.push import notifier_publication
from projets.admin import apercu_video

from .attestation import (
    envoyer_apprenant, envoyer_formateur, envoyer_lot, nom_fichier_apprenant, nom_fichier_formateur,
    pdf_apprenant, pdf_formateur, periode, reponse_pdf, reponse_zip,
)
from .catalogue import CATALOGUE, charger_catalogue
from .models import (
    AttestationFormateur,
    CategorieFormation,
    Formateur,
    Formation,
    FormationSessionPassee,
    Inscription,
    PaiementFormation,
)


class FormationSessionPasseeInline(admin.StackedInline):
    model = FormationSessionPassee
    extra = 0
    fields = (('titre', 'periode'), ('date_debut', 'date_fin'), 'resume', 'lien_video', 'apercu', ('ordre', 'publiee'))
    readonly_fields = ['apercu']
    verbose_name = "Session passée (vidéo YouTube / TikTok)"
    verbose_name_plural = "Sessions passées (vidéos)"

    @admin.display(description='Aperçu')
    def apercu(self, obj):
        return apercu_video(obj.video, 260) if obj.pk else "Enregistrez pour voir l'aperçu."


@admin.register(CategorieFormation)
class CategorieFormationAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'couleur']
    prepopulated_fields = {'slug': ('nom',)}


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    change_list_template = 'admin/formations/formation/change_list.html'
    actions = ['publier', 'masquer', notifier_abonnes]
    list_display = ['vignette', 'titre', 'categorie', 'prix', 'duree', 'places_disponibles', 'actif', 'en_vedette', 'ordre']
    list_display_links = ['titre']
    list_filter = ['actif', 'en_vedette', 'nouveau', 'categorie', 'niveau']
    list_editable = ['actif', 'en_vedette', 'ordre']
    ordering = ['ordre', 'titre']
    search_fields = ['titre', 'description']
    prepopulated_fields = {'slug': ('titre',)}
    filter_horizontal = ['formateurs']
    fieldsets = (
        ('Informations principales', {
            'description': "Une image est obligatoire pour publier la formation (format paysage conseillé, 1600 × 1000 px).",
            'fields': ('titre', 'slug', 'categorie', 'description_courte', 'description', 'image')
        }),
        ('Détails', {
            'fields': ('duree', 'niveau', 'prix', 'prix_avec_base', 'places_disponibles', 'formateurs')
        }),
        ('Contenu pédagogique', {
            'fields': ('objectifs', 'programme', 'prerequis', 'public_cible', 'debouches', 'materiel_fourni')
        }),
        ('Statut et mise en avant', {
            'fields': ('actif', 'ordre', 'en_vedette', 'nouveau')
        }),
    )
    inlines = [FormationSessionPasseeInline]

    @admin.display(description='Image')
    def vignette(self, obj):
        if obj.image:
            return format_html('<img src="{}" alt="" style="width:64px;height:40px;object-fit:cover;border-radius:8px">', obj.image.url)
        return format_html('<span style="display:inline-block;padding:.15rem .5rem;border-radius:999px;background:#FFF6E5;'
                           'color:#B45309;font-size:.72rem;font-weight:700">À ajouter</span>')

    @admin.action(description="Publier les formations sélectionnées (image obligatoire)")
    def publier(self, request, queryset):
        sans_image = list(queryset.filter(Q(image='') | Q(image__isnull=True)).values_list('pk', flat=True))
        nouvelles = list(queryset.exclude(pk__in=sans_image).filter(actif=False).values_list('pk', flat=True))
        n = Formation.objects.filter(pk__in=nouvelles).update(actif=True)
        for formation in Formation.objects.filter(pk__in=nouvelles):   # update() ne déclenche pas les signaux
            notifier_publication(formation)
        if n:
            self.message_user(request, f"{n} formation(s) publiée(s) ; les abonnés ont été prévenus.", messages.SUCCESS)
        if sans_image:
            self.message_user(request, f"{len(sans_image)} formation(s) ignorée(s) : ajoutez d'abord une image.", messages.WARNING)

    @admin.action(description="Masquer les formations sélectionnées")
    def masquer(self, request, queryset):
        n = queryset.update(actif=False)
        self.message_user(request, f"{n} formation(s) masquée(s).", messages.SUCCESS)

    def get_urls(self):
        return [path('charger-catalogue/', self.admin_site.admin_view(self.charger_catalogue_view),
                     name='formations_formation_charger_catalogue')] + super().get_urls()

    def charger_catalogue_view(self, request):
        if request.method != 'POST':
            return redirect('admin:formations_formation_changelist')
        crees, _, inchangees = charger_catalogue(force=False)
        if crees:
            self.message_user(request, f"{crees} formation(s) ajoutée(s), masquées : ajoutez une image puis publiez-les.",
                              messages.SUCCESS)
        else:
            self.message_user(request, "Le catalogue est déjà complet : aucune formation ajoutée.", messages.INFO)
        return redirect('admin:formations_formation_changelist')

    def changelist_view(self, request, extra_context=None):
        qs = Formation.objects.all()
        extra_context = {
            **(extra_context or {}),
            'nb_publiees': qs.filter(actif=True).count(),
            'nb_masquees': qs.filter(actif=False).count(),
            'nb_sans_image': qs.filter(Q(image='') | Q(image__isnull=True)).count(),
            'catalogue_total': len(CATALOGUE),
        }
        return super().changelist_view(request, extra_context=extra_context)


class SessionAttestationForm(forms.Form):
    session_debut = forms.DateField(label="Début de la session", widget=forms.DateInput(attrs={'type': 'date'}))
    session_fin = forms.DateField(label="Fin de la session", widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        donnees = super().clean()
        if donnees.get('session_debut') and donnees.get('session_fin') and donnees['session_fin'] < donnees['session_debut']:
            self.add_error('session_fin', "La fin doit être postérieure au début.")
        return donnees


def _lien_pdf(url):
    return format_html('<a href="{}" target="_blank" class="btn btn-sm btn-outline-primary">'
                       '<i class="fas fa-file-pdf mr-1"></i>PDF</a>', url)


@admin.register(Formateur)
class FormateurAdmin(admin.ModelAdmin):
    list_display = ['nom_complet', 'fonction', 'email', 'telephone', 'nb_formations', 'actif']
    list_display_links = ['nom_complet']
    list_editable = ['actif']
    list_filter = ['actif']
    search_fields = ['nom', 'prenom', 'fonction', 'email']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_formations=Count('formations', distinct=True))

    @admin.display(description='Nom', ordering='nom')
    def nom_complet(self, obj):
        return obj.nom_complet

    @admin.display(description='Formations', ordering='n_formations')
    def nb_formations(self, obj):
        return obj.n_formations


@admin.register(AttestationFormateur)
class AttestationFormateurAdmin(admin.ModelAdmin):
    actions = ['telecharger', 'envoyer']
    list_display = ['formateur', 'formation', 'periode', 'volume_horaire', 'pdf', 'envoyee_le']
    list_filter = ['formation', 'formateur']
    list_select_related = ['formateur', 'formation']
    search_fields = ['formateur__nom', 'formateur__prenom', 'formation__titre']
    autocomplete_fields = ['formateur', 'formation']
    date_hierarchy = 'session_debut'
    fields = ['formateur', 'formation', ('session_debut', 'session_fin'), ('volume_horaire', 'nb_apprenants'),
              'delivree_le', 'pdf', 'envoyee_le']
    readonly_fields = ['pdf', 'envoyee_le']

    @admin.display(description='Session', ordering='session_debut')
    def periode(self, obj):
        return periode(obj.session_debut, obj.session_fin)

    @admin.display(description='Attestation')
    def pdf(self, obj):
        if not obj.pk:
            return "Enregistrez pour générer l'attestation."
        return _lien_pdf(reverse('admin:formations_attestationformateur_pdf', args=[obj.pk]))

    def get_urls(self):
        return [path('<int:pk>/attestation.pdf', self.admin_site.admin_view(self.pdf_view),
                     name='formations_attestationformateur_pdf')] + super().get_urls()

    def pdf_view(self, request, pk):
        attestation = get_object_or_404(AttestationFormateur.objects.select_related('formateur', 'formation'), pk=pk)
        return reponse_pdf(pdf_formateur(attestation), nom_fichier_formateur(attestation))

    @admin.action(description="Télécharger les attestations sélectionnées (PDF / ZIP)")
    def telecharger(self, request, queryset):
        attestations = list(queryset.select_related('formateur', 'formation'))
        if len(attestations) == 1:
            return reponse_pdf(pdf_formateur(attestations[0]), nom_fichier_formateur(attestations[0]))
        return reponse_zip([(nom_fichier_formateur(a), pdf_formateur(a)) for a in attestations],
                           f"KcoMat_attestations_formateurs_{timezone.localdate():%Y-%m-%d}")

    @admin.action(description="Envoyer les attestations sélectionnées par e-mail aux formateurs")
    def envoyer(self, request, queryset):
        avec_email = queryset.select_related('formateur', 'formation').exclude(formateur__email='')
        sans_email = queryset.filter(formateur__email='').count()
        envoyees, echecs = envoyer_lot(avec_email, envoyer_formateur)
        _bilan_envoi(self, request, envoyees, echecs, sans_email, "formateur(s) sans adresse e-mail")


def _bilan_envoi(model_admin, request, envoyees, echecs, ignores, libelle_ignores):
    if envoyees:
        model_admin.message_user(request, f"{envoyees} attestation(s) envoyée(s) par e-mail.", messages.SUCCESS)
    if echecs:
        model_admin.message_user(request, f"Envoi impossible pour : {', '.join(echecs)}. Vérifiez la configuration e-mail.",
                                 messages.ERROR)
    if ignores:
        model_admin.message_user(request, f"{ignores} ignorée(s) : {libelle_ignores}.", messages.WARNING)


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    actions = ['marquer_terminee', 'attestations_telecharger', 'attestations_envoyer']

    def _preparer_attestations(self, request, queryset, action, libelle):
        """Retient les inscriptions payées ; demande les dates de session si elles manquent ou sur demande.
        Renvoie (inscriptions prêtes, None) ou (None, page intermédiaire)."""
        payees = queryset.filter(statut__in=Inscription.STATUTS_PAYES).select_related('formation')
        ignorees = queryset.exclude(statut__in=Inscription.STATUTS_PAYES).count()
        form = None
        if 'appliquer_dates' in request.POST:
            form = SessionAttestationForm(request.POST)
            if form.is_valid():
                payees.update(**form.cleaned_data)
                form = None
        elif payees.filter(Q(session_debut__isnull=True) | Q(session_fin__isnull=True)).exists():
            dates = set(payees.exclude(session_debut__isnull=True).values_list('session_debut', 'session_fin'))
            initial = dict(zip(('session_debut', 'session_fin'), dates.pop())) if len(dates) == 1 else {}
            form = SessionAttestationForm(initial=initial)
        if form is not None:
            return None, TemplateResponse(request, 'admin/formations/inscription/attestations.html', {
                **self.admin_site.each_context(request),
                'title': "Dates de la session pour les attestations",
                'opts': self.model._meta,
                'form': form,
                'inscriptions': payees,
                'ignorees': ignorees,
                'action': action,
                'libelle': libelle,
                'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
                'selection': queryset.values_list('pk', flat=True),
            })
        if ignorees:
            self.message_user(request, f"{ignorees} inscription(s) ignorée(s) : seule une formation entièrement payée "
                                       "donne droit à une attestation.", messages.WARNING)
        inscriptions = list(payees.prefetch_related('formation__formateurs'))
        # attestation délivrée : la formation est terminée (une nouvelle inscription redevient possible)
        payees.filter(statut='complet').update(statut='termine')
        return inscriptions, None

    @admin.action(description="Attestations : télécharger (PDF / ZIP)")
    def attestations_telecharger(self, request, queryset):
        inscriptions, page = self._preparer_attestations(request, queryset, 'attestations_telecharger', "Télécharger")
        if page is not None:
            return page
        if not inscriptions:
            return None
        if len(inscriptions) == 1:
            return reponse_pdf(pdf_apprenant(inscriptions[0]), nom_fichier_apprenant(inscriptions[0]))
        return reponse_zip([(nom_fichier_apprenant(i), pdf_apprenant(i)) for i in inscriptions],
                           f"KcoMat_attestations_formation_{timezone.localdate():%Y-%m-%d}")

    @admin.action(description="Attestations : envoyer par e-mail à chaque inscrit")
    def attestations_envoyer(self, request, queryset):
        inscriptions, page = self._preparer_attestations(request, queryset, 'attestations_envoyer', "Envoyer par e-mail")
        if page is not None:
            return page
        envoyees, echecs = envoyer_lot(inscriptions or [], envoyer_apprenant)
        _bilan_envoi(self, request, envoyees, echecs, 0, '')
        return None

    @admin.action(description="Marquer la formation comme terminée (permet une nouvelle inscription)")
    def marquer_terminee(self, request, queryset):
        n = queryset.filter(statut='complet').update(statut='termine')
        ignores = queryset.exclude(statut__in=['complet', 'termine']).count()
        self.message_user(request, f"{n} inscription(s) marquée(s) « Formation terminée »."
                          + (f" {ignores} ignorée(s) : seule une formation entièrement payée peut être terminée." if ignores else ""),
                          messages.SUCCESS if n else messages.WARNING)

    list_display = ['prenom', 'nom', 'email', 'formation', 'mode_preference', 'statut', 'lien_meet', 'attestation', 'created_at']
    list_filter = ['statut', 'mode_preference', 'formation']
    search_fields = ['nom', 'prenom', 'email', 'telephone']
    readonly_fields = ['created_at', 'frais_payes_le', 'formation_payee_le', 'jitsi_room_created_at', 'lien_meet',
                       'montant_acompte', 'fedapay_acompte_id', 'acompte_paye_le',
                       'attestation', 'attestation_envoyee_le']
    date_hierarchy = 'created_at'
    list_select_related = ['formation']
    change_list_template = 'admin/formations/inscription/change_list.html'

    fieldsets = (
        ('Inscription', {
            'fields': (
                'formation',
                'utilisateur',
                'prenom',
                'nom',
                'email',
                'telephone',
                'adresse',
                'mode_preference',
                'niveau_actuel',
                'message',
                'statut',
            )
        }),
        ('Paiements', {
            'description': "Paiement en 2 tranches : la 1re tranche (50 %) figure ci-dessous ; le solde, comme un "
                           "paiement total, dans « fedapay formation id / formation payée le ».",
            'fields': ('fedapay_frais_id', 'frais_payes_le', ('montant_acompte', 'fedapay_acompte_id', 'acompte_paye_le'),
                       'fedapay_formation_id', 'formation_payee_le')
        }),
        ('Formation en ligne (Jitsi)', {
            'fields': ('jitsi_room_name', 'jitsi_room_created_at', 'lien_meet')
        }),
        ('Attestation de formation', {
            'description': "Disponible une fois la formation payée et les dates de la session renseignées. Pour toute "
                           "une session : cochez les inscrits dans la liste, puis action « Attestations : télécharger » "
                           "ou « envoyer par e-mail ».",
            'fields': (('session_debut', 'session_fin'), 'attestation', 'attestation_envoyee_le')
        }),
        ('Meta', {
            'fields': ('created_at',)
        }),
    )

    @admin.display(description='Salle Meet')
    def lien_meet(self, obj):
        if obj.mode_preference != 'en_ligne':
            return '-'
        embed_url = reverse('formations:meet_room', args=[obj.pk])
        launch_url = reverse('formations:lancer_meet', args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank">Ouvrir la salle intégrée</a> <span style="color:#94a3b8;">|</span> <a href="{}" target="_blank">Lien rapide</a>',
            embed_url,
            launch_url,
        )

    @admin.display(description='Attestation')
    def attestation(self, obj):
        if not obj.pk or obj.statut not in Inscription.STATUTS_PAYES:
            return '—'
        if not obj.attestation_possible:
            return format_html('<span style="color:#B45309;font-size:.8rem">Dates de session à renseigner</span>')
        return _lien_pdf(reverse('admin:formations_inscription_attestation', args=[obj.pk]))

    def attestation_view(self, request, pk):
        inscription = get_object_or_404(Inscription.objects.select_related('formation'), pk=pk)
        if not inscription.attestation_possible:
            self.message_user(request, "Attestation indisponible : formation non payée ou dates de session manquantes.",
                              messages.WARNING)
            return redirect('admin:formations_inscription_change', pk)
        return reponse_pdf(pdf_apprenant(inscription), nom_fichier_apprenant(inscription))

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'report-pdf/',
                self.admin_site.admin_view(self.report_pdf_view),
                name='formations_inscription_report_pdf',
            ),
            path('<int:pk>/attestation.pdf', self.admin_site.admin_view(self.attestation_view),
                 name='formations_inscription_attestation'),
        ]
        return custom_urls + urls

    def _period_config(self, period):
        now = timezone.now()
        mapping = {
            'day': (now - timedelta(days=1), '1 jour'),
            'week': (now - timedelta(days=7), '1 semaine'),
            'month': (now - timedelta(days=30), '1 mois'),
            'year': (now - timedelta(days=365), '1 an'),
        }
        return mapping.get(period, mapping['day'])

    def _paid_amount_for_inscription(self, inscription):
        frais = Decimal(settings.KCOMAT_INFO.get('frais_inscription', 2000))
        formation_price = Decimal(inscription.formation.prix or 0)
        if inscription.statut in ('complet', 'termine') or inscription.formation_payee_le is not None:
            return frais + formation_price
        if inscription.acompte_paye_le is not None:
            return frais + Decimal(inscription.montant_acompte or 0)
        return frais

    def report_pdf_view(self, request):
        period = request.GET.get('period', 'day')
        start_date, period_label = self._period_config(period)

        queryset = Inscription.objects.select_related('formation').filter(
            statut__in=['frais_payes', 'acompte', 'complet', 'termine'],
            created_at__gte=start_date,
        ).order_by('-created_at')

        total_amount = sum((self._paid_amount_for_inscription(i) for i in queryset), Decimal('0'))
        count = queryset.count()

        response = HttpResponse(content_type='application/pdf')
        safe_period = period if period in ['day', 'week', 'month', 'year'] else 'day'
        response['Content-Disposition'] = f'inline; filename="rapport-inscriptions-payees-{safe_period}.pdf"'

        pdf = canvas.Canvas(response, pagesize=landscape(A4))
        width, height = landscape(A4)
        margin = 28
        now_local = timezone.localtime(timezone.now())

        primary = colors.HexColor('#123E78')
        primary_dark = colors.HexColor('#0F2F59')
        border = colors.HexColor('#D6DFEA')
        soft_bg = colors.HexColor('#F4F7FB')
        zebra = colors.HexColor('#FAFCFF')

        def money(v):
            return f"{int(v):,} FCFA".replace(',', ' ')

        def draw_page_header(page_no):
            pdf.setFillColor(primary)
            pdf.rect(0, height - 74, width, 74, stroke=0, fill=1)

            pdf.setFillColor(colors.white)
            pdf.setFont('Helvetica-Bold', 16)
            pdf.drawString(margin, height - 30, 'Rapport inscriptions payees')
            pdf.setFont('Helvetica', 9)
            pdf.drawString(margin, height - 46, f'KcoMat  |  Periode: {period_label}')
            pdf.drawRightString(width - margin, height - 46, f'Genere le: {now_local.strftime("%d/%m/%Y %H:%M")}')

            pdf.setStrokeColor(border)
            pdf.line(margin, 28, width - margin, 28)
            pdf.setFillColor(colors.HexColor('#60738C'))
            pdf.setFont('Helvetica', 8)
            pdf.drawRightString(width - margin, 16, f'Page {page_no}')

        def draw_summary_cards(y_top):
            card_h = 46
            gap = 10
            card_w = (width - (margin * 2) - (gap * 2)) / 3

            cards = [
                ('Inscriptions payees', str(count)),
                ('Total encaisse', money(total_amount)),
                ('Periode', period_label),
            ]

            x = margin
            for label, value in cards:
                pdf.setFillColor(soft_bg)
                pdf.setStrokeColor(border)
                pdf.roundRect(x, y_top - card_h, card_w, card_h, 6, stroke=1, fill=1)
                pdf.setFillColor(primary_dark)
                pdf.setFont('Helvetica-Bold', 8)
                pdf.drawString(x + 10, y_top - 14, label)
                pdf.setFillColor(colors.black)
                pdf.setFont('Helvetica-Bold', 10)
                pdf.drawString(x + 10, y_top - 30, value)
                x += card_w + gap
            return y_top - card_h - 18

        def draw_wrapped_text(text, x_left, x_right, y_top, row_h, max_lines=2):
            value = str(text or '').strip()
            if not value:
                return

            font_name = 'Helvetica'
            font_size = 8
            max_width = max(24, x_right - x_left - 10)
            words = value.split()
            lines = []
            i = 0

            while i < len(words) and len(lines) < max_lines:
                line = words[i]
                i += 1
                while i < len(words):
                    candidate = f'{line} {words[i]}'
                    if pdf.stringWidth(candidate, font_name, font_size) <= max_width:
                        line = candidate
                        i += 1
                    else:
                        break
                lines.append(line)

            truncated = i < len(words)
            if truncated and lines:
                last = lines[-1]
                while last and pdf.stringWidth(f'{last}…', font_name, font_size) > max_width:
                    last = last[:-1].rstrip()
                lines[-1] = f'{last}…' if last else '…'

            pdf.setFont(font_name, font_size)
            line_height = 9
            center_y = y_top - (row_h / 2)
            block_h = (len(lines) - 1) * line_height
            start_y = center_y + (block_h / 2) - 3
            for idx, line in enumerate(lines):
                pdf.drawString(x_left + 5, start_y - (idx * line_height), line)

        def draw_table_header(y_top):
            row_h = 20
            pdf.setFillColor(primary_dark)
            pdf.setStrokeColor(primary_dark)
            pdf.rect(margin, y_top - row_h, width - (margin * 2), row_h, stroke=1, fill=1)

            x_date = margin
            x_participant = x_date + 76
            x_formation = x_participant + 170
            x_email = x_formation + 150
            x_statut = x_email + 185
            x_montant = x_statut + 105

            pdf.setFillColor(colors.white)
            pdf.setFont('Helvetica-Bold', 8.5)
            pdf.drawString(x_date + 5, y_top - 13, 'Date')
            pdf.drawString(x_participant + 5, y_top - 13, 'Participant')
            pdf.drawString(x_formation + 5, y_top - 13, 'Formation')
            pdf.drawString(x_email + 5, y_top - 13, 'Email')
            pdf.drawString(x_statut + 5, y_top - 13, 'Statut')
            pdf.drawRightString(width - margin - 8, y_top - 13, 'Montant')
            return y_top - row_h, {
                'date_left': x_date,
                'date_right': x_participant,
                'participant_left': x_participant,
                'participant_right': x_formation,
                'formation_left': x_formation,
                'formation_right': x_email,
                'email_left': x_email,
                'email_right': x_statut,
                'statut_left': x_statut,
                'statut_right': x_montant,
                'montant_right': width - margin,
            }

        page_no = 1
        draw_page_header(page_no)
        y = draw_summary_cards(height - 90)
        y, cols = draw_table_header(y)

        row_h = 24
        toggle = False
        pdf.setFont('Helvetica', 8)

        if count == 0:
            pdf.setFillColor(colors.HexColor('#6B7C93'))
            pdf.setFont('Helvetica-Oblique', 9)
            pdf.drawString(margin + 8, y - 18, 'Aucune inscription payee sur cette periode.')
        else:
            for inscription in queryset:
                if y < 72:
                    pdf.showPage()
                    page_no += 1
                    draw_page_header(page_no)
                    y, cols = draw_table_header(height - 90)
                    toggle = False
                    pdf.setFont('Helvetica', 8)

                if toggle:
                    pdf.setFillColor(zebra)
                    pdf.rect(margin, y - row_h, width - (margin * 2), row_h, stroke=0, fill=1)

                pdf.setStrokeColor(border)
                pdf.rect(margin, y - row_h, width - (margin * 2), row_h, stroke=1, fill=0)

                date_text = timezone.localtime(inscription.created_at).strftime('%d/%m/%Y')
                participant_text = f'{inscription.prenom} {inscription.nom}'
                formation_text = inscription.formation.titre or ''
                email_text = inscription.email or ''
                statut_text = inscription.get_statut_display()
                amount_text = money(self._paid_amount_for_inscription(inscription))

                pdf.setFillColor(colors.black)
                draw_wrapped_text(date_text, cols['date_left'], cols['date_right'], y, row_h, max_lines=1)
                draw_wrapped_text(participant_text, cols['participant_left'], cols['participant_right'], y, row_h)
                draw_wrapped_text(formation_text, cols['formation_left'], cols['formation_right'], y, row_h)
                draw_wrapped_text(email_text, cols['email_left'], cols['email_right'], y, row_h)
                draw_wrapped_text(statut_text, cols['statut_left'], cols['statut_right'], y, row_h)
                pdf.setFont('Helvetica', 8)
                pdf.drawRightString(cols['montant_right'] - 8, y - 15, amount_text)

                y -= row_h
                toggle = not toggle

        pdf.save()
        return response


@admin.register(PaiementFormation)
class PaiementFormationAdmin(admin.ModelAdmin):
    list_display = [
        'prenom',
        'nom',
        'formation',
        'statut',
        'frais_payes_le',
        'formation_payee_le',
        'montant_encaisse',
    ]
    list_filter = ['statut', 'formation']
    search_fields = ['nom', 'prenom', 'email', 'telephone', 'fedapay_frais_id', 'fedapay_formation_id']
    readonly_fields = [
        'formation',
        'utilisateur',
        'nom',
        'prenom',
        'email',
        'telephone',
        'adresse',
        'niveau_actuel',
        'mode_preference',
        'message',
        'statut',
        'fedapay_frais_id',
        'frais_payes_le',
        'fedapay_formation_id',
        'formation_payee_le',
        'jitsi_room_name',
        'jitsi_room_created_at',
        'created_at',
    ]
    date_hierarchy = 'created_at'
    list_select_related = ['formation']
    change_list_template = 'admin/formations/paiementformation/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'report-pdf/',
                self.admin_site.admin_view(self.report_pdf_view),
                name='formations_paiementformation_report_pdf',
            ),
        ]
        return custom_urls + urls

    def _period_config(self, period):
        now = timezone.now()
        mapping = {
            'day': (now - timedelta(days=1), '1 jour'),
            'week': (now - timedelta(days=7), '1 semaine'),
            'month': (now - timedelta(days=30), '1 mois'),
            'year': (now - timedelta(days=365), '1 an'),
        }
        return mapping.get(period, mapping['day'])

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(statut__in=['frais_payes', 'acompte', 'complet', 'termine'])

    @admin.display(description='Montant encaissé')
    def montant_encaisse(self, obj):
        frais = Decimal(settings.KCOMAT_INFO.get('frais_inscription', 2000))
        if obj.statut in ('complet', 'termine') or obj.formation_payee_le is not None:
            montant = frais + Decimal(obj.formation.prix or 0)
        elif obj.acompte_paye_le is not None:
            montant = frais + Decimal(obj.montant_acompte or 0)
        else:
            montant = frais
        return f"{int(montant):,} FCFA".replace(',', ' ')

    def has_add_permission(self, request):
        return False

    def report_pdf_view(self, request):
        period = request.GET.get('period', 'day')
        start_date, period_label = self._period_config(period)

        queryset = self.get_queryset(request).filter(created_at__gte=start_date).order_by('-created_at')

        total_amount = sum((Decimal(self.montant_encaisse_value(i)) for i in queryset), Decimal('0'))
        count = queryset.count()

        response = HttpResponse(content_type='application/pdf')
        safe_period = period if period in ['day', 'week', 'month', 'year'] else 'day'
        response['Content-Disposition'] = f'inline; filename="rapport-paiements-formation-{safe_period}.pdf"'

        pdf = canvas.Canvas(response, pagesize=landscape(A4))
        width, height = landscape(A4)
        margin = 28
        now_local = timezone.localtime(timezone.now())

        primary = colors.HexColor('#123E78')
        primary_dark = colors.HexColor('#0F2F59')
        border = colors.HexColor('#D6DFEA')
        soft_bg = colors.HexColor('#F4F7FB')
        zebra = colors.HexColor('#FAFCFF')

        def money(v):
            return f"{int(v):,} FCFA".replace(',', ' ')

        def draw_page_header(page_no):
            pdf.setFillColor(primary)
            pdf.rect(0, height - 74, width, 74, stroke=0, fill=1)

            pdf.setFillColor(colors.white)
            pdf.setFont('Helvetica-Bold', 16)
            pdf.drawString(margin, height - 30, 'Rapport paiements formation')
            pdf.setFont('Helvetica', 9)
            pdf.drawString(margin, height - 46, f'KcoMat  |  Periode: {period_label}')
            pdf.drawRightString(width - margin, height - 46, f'Genere le: {now_local.strftime("%d/%m/%Y %H:%M")}')

            pdf.setStrokeColor(border)
            pdf.line(margin, 28, width - margin, 28)
            pdf.setFillColor(colors.HexColor('#60738C'))
            pdf.setFont('Helvetica', 8)
            pdf.drawRightString(width - margin, 16, f'Page {page_no}')

        def draw_summary_cards(y_top):
            card_h = 46
            gap = 10
            card_w = (width - (margin * 2) - (gap * 2)) / 3

            cards = [
                ('Paiements', str(count)),
                ('Total encaisse', money(total_amount)),
                ('Periode', period_label),
            ]

            x = margin
            for label, value in cards:
                pdf.setFillColor(soft_bg)
                pdf.setStrokeColor(border)
                pdf.roundRect(x, y_top - card_h, card_w, card_h, 6, stroke=1, fill=1)
                pdf.setFillColor(primary_dark)
                pdf.setFont('Helvetica-Bold', 8)
                pdf.drawString(x + 10, y_top - 14, label)
                pdf.setFillColor(colors.black)
                pdf.setFont('Helvetica-Bold', 10)
                pdf.drawString(x + 10, y_top - 30, value)
                x += card_w + gap
            return y_top - card_h - 18

        def draw_wrapped_text(text, x_left, x_right, y_top, row_h, max_lines=2):
            value = str(text or '').strip()
            if not value:
                return

            font_name = 'Helvetica'
            font_size = 8
            max_width = max(24, x_right - x_left - 10)
            words = value.split()
            lines = []
            i = 0

            while i < len(words) and len(lines) < max_lines:
                line = words[i]
                i += 1
                while i < len(words):
                    candidate = f'{line} {words[i]}'
                    if pdf.stringWidth(candidate, font_name, font_size) <= max_width:
                        line = candidate
                        i += 1
                    else:
                        break
                lines.append(line)

            truncated = i < len(words)
            if truncated and lines:
                last = lines[-1]
                while last and pdf.stringWidth(f'{last}…', font_name, font_size) > max_width:
                    last = last[:-1].rstrip()
                lines[-1] = f'{last}…' if last else '…'

            pdf.setFont(font_name, font_size)
            line_height = 9
            center_y = y_top - (row_h / 2)
            block_h = (len(lines) - 1) * line_height
            start_y = center_y + (block_h / 2) - 3
            for idx, line in enumerate(lines):
                pdf.drawString(x_left + 5, start_y - (idx * line_height), line)

        def draw_table_header(y_top):
            row_h = 20
            pdf.setFillColor(primary_dark)
            pdf.setStrokeColor(primary_dark)
            pdf.rect(margin, y_top - row_h, width - (margin * 2), row_h, stroke=1, fill=1)

            x_date = margin
            x_participant = x_date + 76
            x_formation = x_participant + 170
            x_email = x_formation + 150
            x_statut = x_email + 185
            x_montant = x_statut + 105

            pdf.setFillColor(colors.white)
            pdf.setFont('Helvetica-Bold', 8.5)
            pdf.drawString(x_date + 5, y_top - 13, 'Date')
            pdf.drawString(x_participant + 5, y_top - 13, 'Participant')
            pdf.drawString(x_formation + 5, y_top - 13, 'Formation')
            pdf.drawString(x_email + 5, y_top - 13, 'Email')
            pdf.drawString(x_statut + 5, y_top - 13, 'Statut')
            pdf.drawRightString(width - margin - 8, y_top - 13, 'Montant')
            return y_top - row_h, {
                'date_left': x_date,
                'date_right': x_participant,
                'participant_left': x_participant,
                'participant_right': x_formation,
                'formation_left': x_formation,
                'formation_right': x_email,
                'email_left': x_email,
                'email_right': x_statut,
                'statut_left': x_statut,
                'statut_right': x_montant,
                'montant_right': width - margin,
            }

        page_no = 1
        draw_page_header(page_no)
        y = draw_summary_cards(height - 90)
        y, cols = draw_table_header(y)

        row_h = 24
        toggle = False
        pdf.setFont('Helvetica', 8)

        if count == 0:
            pdf.setFillColor(colors.HexColor('#6B7C93'))
            pdf.setFont('Helvetica-Oblique', 9)
            pdf.drawString(margin + 8, y - 18, 'Aucun paiement sur cette periode.')
        else:
            for inscription in queryset:
                if y < 72:
                    pdf.showPage()
                    page_no += 1
                    draw_page_header(page_no)
                    y, cols = draw_table_header(height - 90)
                    toggle = False
                    pdf.setFont('Helvetica', 8)

                if toggle:
                    pdf.setFillColor(zebra)
                    pdf.rect(margin, y - row_h, width - (margin * 2), row_h, stroke=0, fill=1)

                pdf.setStrokeColor(border)
                pdf.rect(margin, y - row_h, width - (margin * 2), row_h, stroke=1, fill=0)

                date_text = timezone.localtime(inscription.created_at).strftime('%d/%m/%Y')
                participant_text = f'{inscription.prenom} {inscription.nom}'
                formation_text = inscription.formation.titre or ''
                email_text = inscription.email or ''
                statut_text = inscription.get_statut_display()
                amount_text = money(self.montant_encaisse_value(inscription))

                pdf.setFillColor(colors.black)
                draw_wrapped_text(date_text, cols['date_left'], cols['date_right'], y, row_h, max_lines=1)
                draw_wrapped_text(participant_text, cols['participant_left'], cols['participant_right'], y, row_h)
                draw_wrapped_text(formation_text, cols['formation_left'], cols['formation_right'], y, row_h)
                draw_wrapped_text(email_text, cols['email_left'], cols['email_right'], y, row_h)
                draw_wrapped_text(statut_text, cols['statut_left'], cols['statut_right'], y, row_h)
                pdf.setFont('Helvetica', 8)
                pdf.drawRightString(cols['montant_right'] - 8, y - 15, amount_text)

                y -= row_h
                toggle = not toggle

        pdf.save()
        return response

    def montant_encaisse_value(self, obj):
        frais = Decimal(settings.KCOMAT_INFO.get('frais_inscription', 2000))
        if obj.statut in ('complet', 'termine') or obj.formation_payee_le is not None:
            return frais + Decimal(obj.formation.prix or 0)
        if obj.acompte_paye_le is not None:
            return frais + Decimal(obj.montant_acompte or 0)
        return frais
