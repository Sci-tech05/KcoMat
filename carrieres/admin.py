import calendar
import logging
import mimetypes
from datetime import date

from django.contrib import admin, messages
from django.db.models import Avg, Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .catalogue import DOMAINES, charger_catalogue
from .exports import STATUT_COLORS, rapport_pdf, zip_dossiers
from .models import Candidature, FormuleOffre, Offre
from .notifications import REPONSES, document_filename, envoyer_reponse
from notifications.admin import notifier_abonnes
from notifications.push import notifier_publication

logger = logging.getLogger(__name__)

MOIS_FR = ['', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
           'août', 'septembre', 'octobre', 'novembre', 'décembre']


class FormuleOffreInline(admin.TabularInline):
    model = FormuleOffre
    extra = 0
    fields = ['duree', 'montant', 'description', 'recommandee', 'ordre']
    verbose_name = "Formule"
    verbose_name_plural = "Formules : durée et montant (ex. 1 mois · 20 000 FCFA)"


@admin.register(Offre)
class OffreAdmin(admin.ModelAdmin):
    change_list_template = 'admin/carrieres/offre/change_list.html'
    list_display = ['apercu', 'titre_offre', 'type_offre', 'domaine', 'formules_resume', 'date_limite',
                    'nb_candidatures', 'mise_en_avant', 'actif']
    list_display_links = ['apercu', 'titre_offre']
    list_filter = ['actif', 'type_offre', 'domaine', 'mise_en_avant']
    list_editable = ['mise_en_avant', 'actif']
    search_fields = ['titre', 'accroche', 'description']
    prepopulated_fields = {'slug': ('titre',)}
    inlines = [FormuleOffreInline]
    actions = ['publier', 'masquer', notifier_abonnes]
    fieldsets = (
        ('Publication', {'fields': ('actif', 'mise_en_avant', 'image', 'date_limite', 'places'),
                         'description': "Une image est obligatoire pour publier l'offre."}),
        ('Offre', {'fields': ('titre', 'slug', 'type_offre', 'domaine', 'localite', 'niveau_requis', 'accroche')}),
        ('Contenu', {'fields': ('description', 'missions', 'competences_requises', 'profil', 'avantages')}),
        ('Montant', {'fields': ('nature_montant', 'remuneration'),
                     'description': "Les formules (durée et montant) se règlent dans le tableau en bas de page."}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_nb=Count('candidatures')).prefetch_related('formules')

    @admin.display(description='')
    def apercu(self, obj):
        if obj.image:
            return format_html('<img src="{}" alt="" style="width:64px;height:42px;object-fit:cover;border-radius:8px">', obj.image.url)
        return format_html('<span title="Image manquante : publication impossible" style="display:inline-grid;place-items:center;'
                           'width:64px;height:42px;border-radius:8px;background:#FFF4E6;color:#C2410C;font-size:.68rem;font-weight:700">'
                           '<i class="fas fa-image"></i>À ajouter</span>')

    @admin.display(description='Offre', ordering='titre')
    def titre_offre(self, obj):
        return format_html('<b>{}</b><br><span style="color:#64748B;font-size:.8rem">{}</span>', obj.titre, obj.accroche[:90])

    @admin.display(description='Formules')
    def formules_resume(self, obj):
        formules = list(obj.formules.all())
        if not formules:
            return obj.remuneration or '—'
        return format_html_join('<br>', '<span style="white-space:nowrap">{}</span>', ((str(f),) for f in formules))

    @admin.display(description='Candidatures', ordering='_nb')
    def nb_candidatures(self, obj):
        url = reverse('admin:carrieres_candidature_changelist') + f'?offre__id__exact={obj.pk}'
        return format_html('<a href="{}"><b>{}</b></a>', url, obj._nb)

    @admin.action(description="Publier les offres sélectionnées")
    def publier(self, request, queryset):
        sans_image = queryset.filter(Q(image='') | Q(image__isnull=True))
        n_sans_image = sans_image.count()
        a_publier = queryset.exclude(pk__in=sans_image).filter(actif=False)
        nouvelles = list(a_publier.values_list('pk', flat=True))
        n = a_publier.update(actif=True)
        # update() ne déclenche pas les signaux : on prévient les abonnés ici
        for offre in Offre.objects.filter(pk__in=nouvelles):
            if not offre.est_cloturee:
                notifier_publication(offre)
        if n:
            self.message_user(request, f"{n} offre(s) publiée(s).", messages.SUCCESS)
        if n_sans_image:
            self.message_user(request, f"{n_sans_image} offre(s) non publiée(s) : ajoutez d'abord une image.", messages.WARNING)

    @admin.action(description="Masquer les offres sélectionnées")
    def masquer(self, request, queryset):
        self.message_user(request, f"{queryset.update(actif=False)} offre(s) masquée(s).", messages.SUCCESS)

    def get_urls(self):
        return [path('charger-catalogue/', self.admin_site.admin_view(self.charger_catalogue_view),
                     name='carrieres_offre_charger_catalogue')] + super().get_urls()

    def charger_catalogue_view(self, request):
        if request.method != 'POST' or not self.has_add_permission(request):
            raise Http404
        crees, _, inchangees = charger_catalogue(force=False)
        if crees:
            self.message_user(request, f"{crees} offre(s) type ajoutée(s), masquées : ajoutez une image puis publiez celles "
                                       "que vous souhaitez afficher.", messages.SUCCESS)
        else:
            self.message_user(request, "Le catalogue est déjà complet : aucune offre ajoutée.", messages.INFO)
        return redirect(reverse('admin:carrieres_offre_changelist') + '?actif__exact=0')

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            'nb_publiees': Offre.objects.filter(actif=True).count(),
            'nb_masquees': Offre.objects.filter(actif=False).count(),
            'nb_sans_image': Offre.objects.filter(Q(image='') | Q(image__isnull=True)).count(),
            'catalogue_total': len(DOMAINES) * 3,
        }
        return super().changelist_view(request, extra_context=extra_context)


class PotentielFilter(admin.SimpleListFilter):
    title = 'potentiel'
    parameter_name = 'potentiel'

    def lookups(self, request, model_admin):
        return [('fort', '★★★★ et plus'), ('moyen', '★★★'), ('faible', '★★ et moins'), ('aucun', 'Non évalué')]

    def queryset(self, request, queryset):
        return {
            'fort': queryset.filter(note__gte=4),
            'moyen': queryset.filter(note=3),
            'faible': queryset.filter(note__lte=2),
            'aucun': queryset.filter(note__isnull=True),
        }.get(self.value(), queryset)


def _prevenir_candidat(candidature):
    """E-mail automatique au passage en Entretien / Retenue / Refusée. Retourne None, 'envoye' ou 'echec'."""
    if candidature.statut not in REPONSES:
        return None
    try:
        envoyer_reponse(candidature)
        return 'envoye'
    except Exception:
        logger.exception("Envoi automatique de la réponse impossible pour la candidature #%s", candidature.pk)
        return 'echec'


def _changer_statut(statut):
    def action(modeladmin, request, queryset):
        n, envoyes, echecs = 0, 0, 0
        for candidature in queryset.select_related('offre'):
            if candidature.statut != statut:
                candidature.statut = statut
                candidature.save()
                n += 1
                resultat = _prevenir_candidat(candidature)
                envoyes += resultat == 'envoye'
                echecs += resultat == 'echec'
        label = dict(Candidature.STATUT_CHOICES)[statut]
        modeladmin.message_user(request, f"{n} candidature(s) passée(s) en « {label} ».", messages.SUCCESS)
        if envoyes:
            modeladmin.message_user(request, f"{envoyes} candidat(s) prévenu(s) par e-mail.", messages.SUCCESS)
        if echecs:
            modeladmin.message_user(request, f"{echecs} e-mail(s) non envoyé(s) : vérifiez la configuration e-mail.", messages.ERROR)
    action.__name__ = f'marquer_{statut}'
    action.short_description = f"Statut → {dict(Candidature.STATUT_CHOICES)[statut]}"
    return action


@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    change_list_template = 'admin/carrieres/candidature/change_list.html'
    list_display = ['candidat', 'offre_badge', 'statut', 'note', 'pre_score', 'documents', 'created_at']
    list_display_links = ['candidat']
    list_editable = ['statut', 'note']
    list_filter = ['statut', PotentielFilter, 'offre__type_offre', 'offre']
    list_select_related = ['offre', 'formule']
    search_fields = ['nom', 'prenom', 'email', 'telephone', 'offre__titre']
    date_hierarchy = 'created_at'
    list_per_page = 50
    ordering = ['-created_at']
    readonly_fields = ['documents_detail', 'score_detail', 'created_at', 'statut_modifie_le', 'reponse_envoyee_le']
    fieldsets = (
        ('Évaluation', {'fields': ('statut', 'note', 'score_detail', 'notes_internes'),
                        'description': "Changer le statut prévient le candidat par e-mail : « Entretien » lui envoie "
                                       "le texte des Notes internes (date, heure, lieu…), « Retenue » et « Refusée » "
                                       "un message adapté."}),
        ('Candidat', {'fields': ('offre', 'formule', 'prenom', 'nom', 'email', 'telephone', 'message')}),
        ('Documents', {'fields': ('documents_detail', 'cv', 'lettre_motivation')}),
        ('Historique', {'fields': ('created_at', 'statut_modifie_le', 'reponse_envoyee_le')}),
    )
    actions = [
        _changer_statut(Candidature.STATUT_EN_REVUE),
        _changer_statut(Candidature.STATUT_PRESELECTIONNEE),
        _changer_statut(Candidature.STATUT_ENTRETIEN),
        _changer_statut(Candidature.STATUT_RETENUE),
        _changer_statut(Candidature.STATUT_REFUSEE),
        'telecharger_dossiers_zip',
        'exporter_rapport_pdf',
        'envoyer_reponses',
    ]

    def save_model(self, request, obj, form, change):
        # Fiche ou liste modifiable : e-mail au candidat seulement si le statut vient de changer
        ancien = Candidature.objects.filter(pk=obj.pk).values_list('statut', flat=True).first() if change else None
        super().save_model(request, obj, form, change)
        if obj.statut == ancien:
            return
        resultat = _prevenir_candidat(obj)
        if resultat == 'envoye':
            self.message_user(request, f"E-mail « {obj.get_statut_display()} » envoyé à {obj.email}.", messages.SUCCESS)
        elif resultat == 'echec':
            self.message_user(request, f"Statut enregistré, mais l'e-mail à {obj.email} n'a pas pu partir : "
                                       "vérifiez la configuration e-mail.", messages.ERROR)

    # ------------------------------------------------------------------ colonnes
    @admin.display(description='Candidat', ordering='nom')
    def candidat(self, obj):
        return format_html('<b>{}</b><br><span style="color:#64748B;font-size:.8rem">{}</span>', obj.nom_complet, obj.email)

    @admin.display(description='Offre', ordering='offre__titre')
    def offre_badge(self, obj):
        couleurs = {'emploi': ('#EAF3FF', '#1D4ED8'), 'stage': ('#F1ECFF', '#6D28D9'), 'freelance': ('#FFF4E6', '#C2410C')}
        fond, texte = couleurs.get(obj.offre.type_offre, ('#F1F5F9', '#334155'))
        return format_html(
            '<span style="display:inline-block;padding:.1rem .5rem;border-radius:999px;background:{};color:{};'
            'font-size:.72rem;font-weight:700">{}</span><br><span style="font-size:.85rem">{}</span>{}',
            fond, texte, obj.offre.get_type_offre_display(), obj.offre.titre,
            format_html('<br><span style="font-size:.75rem;color:#2563EB;font-weight:600">{}</span>', obj.formule) if obj.formule_id else '',
        )

    @admin.display(description='Pré-score', ordering='score_auto')
    def pre_score(self, obj):
        couleur = '#10B981' if obj.score_auto >= 70 else '#F59E0B' if obj.score_auto >= 45 else '#F43F5E'
        return format_html(
            '<div title="Pré-score automatique" style="min-width:5.5rem"><b>{}</b><span style="color:#94A3B8">/100</span>'
            '<div style="height:5px;border-radius:9px;background:#EEF2F7;margin-top:4px">'
            '<div style="height:5px;border-radius:9px;width:{}%;background:{}"></div></div></div>',
            obj.score_auto, obj.score_auto, couleur,
        )

    @admin.display(description='Dossier')
    def documents(self, obj):
        liens = []
        if obj.cv:
            liens.append(('CV', reverse('admin:carrieres_candidature_document', args=[obj.pk, 'cv'])))
        if obj.lettre_motivation:
            liens.append(('Lettre', reverse('admin:carrieres_candidature_document', args=[obj.pk, 'lettre'])))
        if not liens:
            return '—'
        return format_html_join(
            ' ', '<a href="{}" target="_blank" rel="noopener" class="btn btn-xs btn-default"><i class="fas fa-file-pdf"></i> {}</a>',
            ((url, label) for label, url in liens),
        )

    @admin.display(description='Fichiers')
    def documents_detail(self, obj):
        return self.documents(obj) if obj.pk else '—'

    @admin.display(description='Détail du pré-score')
    def score_detail(self, obj):
        if not obj.pk:
            return '—'
        lignes = format_html_join(
            '', '<tr><td style="padding:.2rem .8rem .2rem 0">{} {}</td><td style="text-align:right"><b>{}</b>/{}</td></tr>',
            (('✓' if pts == maxi else '·', label, pts, maxi) for label, pts, maxi in obj.score_details()),
        )
        return format_html('<table style="font-size:.85rem">{}<tr><td><b>Total</b></td>'
                           '<td style="text-align:right"><b>{}</b>/100</td></tr></table>', lignes, obj.score_auto)

    # ------------------------------------------------------------------ URLs
    def get_urls(self):
        custom = [
            path('<int:pk>/document/<str:kind>/', self.admin_site.admin_view(self.document_view),
                 name='carrieres_candidature_document'),
            path('export/retenues.zip', self.admin_site.admin_view(self.export_retenues_view),
                 name='carrieres_candidature_export_retenues'),
            path('export/rapport.pdf', self.admin_site.admin_view(self.export_rapport_view),
                 name='carrieres_candidature_export_rapport'),
        ]
        return custom + super().get_urls()

    def document_view(self, request, pk, kind):
        """Sert le CV / la lettre uniquement au staff autorisé (fichiers personnels)."""
        if not self.has_view_permission(request):
            raise Http404
        candidature = get_object_or_404(Candidature, pk=pk)
        field = {'cv': candidature.cv, 'lettre': candidature.lettre_motivation}.get(kind)
        if not field:
            raise Http404
        try:
            fh = field.open('rb')
        except (FileNotFoundError, OSError):
            raise Http404("Fichier introuvable sur le serveur.")
        filename = document_filename(candidature, kind, field.name)
        return FileResponse(fh, as_attachment=not filename.endswith('.pdf'), filename=filename,
                            content_type=mimetypes.guess_type(filename)[0] or 'application/octet-stream')

    # ------------------------------------------------------------------ période
    def _periode(self, request):
        """Mois choisi via la navigation par date de l'admin (sinon le mois courant)."""
        today = timezone.localdate()
        try:
            year = int(request.GET.get('created_at__year') or request.GET.get('year') or today.year)
            month = int(request.GET.get('created_at__month') or request.GET.get('month') or
                        (today.month if not request.GET.get('created_at__year') else 0))
        except ValueError:
            year, month = today.year, today.month
        if month:
            debut = date(year, month, 1)
            fin = date(year, month, calendar.monthrange(year, month)[1])
            libelle = f"{MOIS_FR[month]} {year}"
        else:
            debut, fin, libelle = date(year, 1, 1), date(year, 12, 31), f"année {year}"
        return debut, fin, libelle, year, month

    def _candidatures_periode(self, debut, fin):
        return Candidature.objects.select_related('offre').filter(
            created_at__date__gte=debut, created_at__date__lte=fin)

    def export_retenues_view(self, request):
        debut, fin, libelle, year, month = self._periode(request)
        qs = self._candidatures_periode(debut, fin).filter(statut=Candidature.STATUT_RETENUE).order_by('nom')
        return zip_dossiers(qs, f"KcoMat_candidatures_retenues_{year}-{month:02d}" if month else f"KcoMat_candidatures_retenues_{year}")

    def export_rapport_view(self, request):
        debut, fin, libelle, year, month = self._periode(request)
        qs = self._candidatures_periode(debut, fin).order_by('-note', '-score_auto', '-created_at')
        return rapport_pdf(qs, f"Candidatures — {libelle}",
                           f"Du {debut:%d/%m/%Y} au {fin:%d/%m/%Y} · classées par potentiel puis pré-score",
                           f"KcoMat_rapport_candidatures_{year}-{month:02d}" if month else f"KcoMat_rapport_candidatures_{year}")

    # ------------------------------------------------------------------ synthèse du mois
    def changelist_view(self, request, extra_context=None):
        debut, fin, libelle, year, month = self._periode(request)
        qs = self._candidatures_periode(debut, fin)
        stats = qs.aggregate(total=Count('id'), score=Avg('score_auto'), note=Avg('note'),
                             a_traiter=Count('id', filter=Q(statut__in=['nouvelle', 'en_revue'])),
                             retenues=Count('id', filter=Q(statut='retenue')))
        par_statut = dict(qs.values_list('statut').annotate(n=Count('id')))
        par_type = dict(qs.values_list('offre__type_offre').annotate(n=Count('id')))
        query = f"?year={year}&month={month}"
        extra_context = {
            **(extra_context or {}),
            'mois_libelle': libelle,
            'mois_stats': stats,
            'mois_statuts': [(code, label, par_statut.get(code, 0), STATUT_COLORS[code]) for code, label in Candidature.STATUT_CHOICES],
            'mois_types': [(label, par_type.get(code, 0)) for code, label in Offre.TYPE_CHOICES],
            'mois_top': qs.exclude(statut='refusee').order_by('-note', '-score_auto', '-created_at')[:5],
            'export_zip_url': reverse('admin:carrieres_candidature_export_retenues') + query,
            'export_pdf_url': reverse('admin:carrieres_candidature_export_rapport') + query,
        }
        return super().changelist_view(request, extra_context=extra_context)

    # ------------------------------------------------------------------ actions
    @admin.action(description="Télécharger les dossiers (ZIP : CV + lettres + index)")
    def telecharger_dossiers_zip(self, request, queryset):
        return zip_dossiers(queryset.select_related('offre').order_by('statut', 'nom'),
                            f"KcoMat_dossiers_{timezone.localdate():%Y-%m-%d}")

    @admin.action(description="Exporter la sélection en PDF")
    def exporter_rapport_pdf(self, request, queryset):
        qs = queryset.select_related('offre').order_by('-note', '-score_auto')
        return rapport_pdf(qs, "Candidatures sélectionnées", f"{qs.count()} candidature(s) · export du {timezone.localdate():%d/%m/%Y}",
                           f"KcoMat_selection_candidatures_{timezone.localdate():%Y-%m-%d}")

    @admin.action(description="Envoyer l'e-mail de réponse (entretien / retenue / refusée)")
    def envoyer_reponses(self, request, queryset):
        envoyees, ignorees, erreurs = 0, 0, 0
        for candidature in queryset.select_related('offre'):
            try:
                if envoyer_reponse(candidature):
                    envoyees += 1
                else:
                    ignorees += 1
            except Exception:
                erreurs += 1
                logger.exception("Envoi de la réponse impossible pour la candidature #%s", candidature.pk)
        if envoyees:
            self.message_user(request, f"{envoyees} e-mail(s) de réponse envoyé(s).", messages.SUCCESS)
        if ignorees:
            self.message_user(request, f"{ignorees} candidature(s) ignorée(s) : statut sans réponse type "
                                       "(seuls Entretien, Retenue et Refusée déclenchent un e-mail).", messages.WARNING)
        if erreurs:
            self.message_user(request, f"{erreurs} envoi(s) en échec : vérifiez la configuration e-mail.", messages.ERROR)
