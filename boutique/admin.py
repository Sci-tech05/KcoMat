import logging

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from datetime import timedelta

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from core.templatetags.kcomat_tags import webp

from .catalogue import charger_catalogue, nombre_produits
from .images import image_depuis_lien
from .models import CategorieProduit, Produit, ProduitRetire, ImageProduit, Commande, CommandeItem
from .suivi import envoyer_email_suivi, raison_echec_email

logger = logging.getLogger(__name__)


@admin.register(CategorieProduit)
class CategorieProduitAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'ordre']
    list_editable = ['ordre']
    prepopulated_fields = {'slug': ('nom',)}


@admin.register(ProduitRetire)
class ProduitRetireAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'retire_le']
    search_fields = ['nom', 'slug']
    readonly_fields = ['nom', 'slug', 'retire_le']

    actions = ['supprimer_definitivement', 'autoriser_retour']

    def get_queryset(self, request):
        # les composants supprimés définitivement ne s'affichent plus (mais restent bloqués)
        return super().get_queryset(request).filter(definitif=False)

    def has_add_permission(self, request):
        return False  # ajouté automatiquement quand un composant du catalogue est supprimé

    def has_delete_permission(self, request, obj=None):
        return False  # supprimer la ligne ferait revenir le composant : voir les actions ci-dessous

    def get_actions(self, request):
        actions = super().get_actions(request)
        if request.user.has_perm('boutique.change_produitretire'):
            return actions
        return {}

    @admin.action(description="Supprimer définitivement (le composant ne reviendra jamais)")
    def supprimer_definitivement(self, request, queryset):
        n = queryset.update(definitif=True)
        self.message_user(request, f"{n} composant(s) supprimé(s) définitivement : ils ne reviendront plus dans la boutique, "
                                   "même en rechargeant le catalogue.", messages.SUCCESS)

    @admin.action(description="Autoriser le retour au prochain « Charger le catalogue »")
    def autoriser_retour(self, request, queryset):
        n, _ = queryset.delete()
        self.message_user(request, f"{n} composant(s) seront recréés (masqués) au prochain « Charger le catalogue ».",
                          messages.SUCCESS)

    def changelist_view(self, request, extra_context=None):
        if request.method == 'GET':
            self.message_user(request, "Ces composants du catalogue ont été supprimés : « Charger le catalogue » ne les recrée plus. "
                                       "Sélectionnez-les puis « Supprimer définitivement » pour les faire disparaître de cette liste "
                                       "pour toujours, ou « Autoriser le retour » pour les récupérer.", messages.INFO)
        return super().changelist_view(request, extra_context)


class ImageProduitInline(admin.TabularInline):
    model = ImageProduit
    extra = 2
    fields = ['image', 'alt', 'ordre']


class ProduitAdminForm(forms.ModelForm):
    image_lien = forms.URLField(
        label="Image depuis un lien", required=False, assume_scheme='https',
        help_text="Collez l'adresse d'une image (clic droit sur l'image → « Copier l'adresse de l'image »). "
                  "Elle est téléchargée une fois, réduite et compressée en WebP : le site reste léger. "
                  "Remplace l'image principale actuelle. N'utilisez que des images dont vous avez le droit "
                  "(vos photos, images fabricant, photos libres de droits).",
    )

    class Meta:
        model = Produit
        fields = '__all__'

    def clean_image_lien(self):
        lien = self.cleaned_data.get('image_lien')
        # téléchargé ici pour afficher l'erreur sous le champ si le lien ne convient pas
        self.image_importee = image_depuis_lien(lien) if lien else None
        return lien


class ProduitActionForm(ActionForm):
    # case affichée à côté de la liste des actions, utilisée par « Mettre le stock à la quantité saisie »
    quantite = forms.IntegerField(
        required=False, min_value=0, label='Quantité',
        widget=forms.NumberInput(attrs={'placeholder': 'Quantité', 'min': 0, 'class': 'form-control',
                                        'style': 'width:7.5rem;display:inline-block;margin-left:.5rem'}),
    )


class SansImageFilter(admin.SimpleListFilter):
    title = 'photo'
    parameter_name = 'photo'

    def lookups(self, request, model_admin):
        return [('non', 'Sans photo'), ('oui', 'Avec photo')]

    def queryset(self, request, queryset):
        sans_photo = Q(image='') | Q(image__isnull=True)
        if self.value() == 'non':
            return queryset.filter(sans_photo)
        if self.value() == 'oui':
            return queryset.exclude(sans_photo)
        return queryset


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    form = ProduitAdminForm
    list_display = ['miniature', 'nom', 'categorie', 'prix', 'stock', 'actif', 'en_vedette', 'nouveau']
    list_display_links = ['miniature', 'nom']
    list_filter = ['actif', SansImageFilter, 'en_vedette', 'nouveau', 'categorie']
    list_select_related = ['categorie']
    fields = ['categorie', 'nom', 'slug', 'reference', 'description_courte', 'description',
              'apercu', 'image', 'image_lien', 'credit_image', 'source_image', 'prix', 'stock', 'actif', 'nouveau', 'en_vedette']
    readonly_fields = ['apercu']
    list_editable = ['actif', 'en_vedette', 'prix', 'stock']
    search_fields = ['nom', 'reference', 'description']
    prepopulated_fields = {'slug': ('nom',)}
    inlines = [ImageProduitInline]
    change_list_template = 'admin/boutique/produit/change_list.html'
    action_form = ProduitActionForm
    actions = ['definir_stock', 'publier', 'masquer']

    @admin.action(description="Mettre le stock des produits sélectionnés à la quantité saisie")
    def definir_stock(self, request, queryset):
        try:
            quantite = int(request.POST.get('quantite', ''))
        except ValueError:
            quantite = -1
        if quantite < 0:
            self.message_user(request, "Saisissez la quantité (nombre entier, 0 ou plus) dans la case « Quantité » "
                                       "à côté de l'action, puis relancez.", messages.ERROR)
            return
        nombre = queryset.update(stock=quantite)
        self.message_user(request, f"Stock mis à {quantite} pour {nombre} produit(s).", messages.SUCCESS)

    @admin.display(description='Photo')
    def miniature(self, obj):
        if not obj.image:
            return format_html('<span style="color:#94A3B8">—</span>')
        return format_html('<img src="{}" alt="" style="width:44px;height:44px;object-fit:contain;'
                           'border-radius:8px;background:#fff;border:1px solid #E2E8F0">', webp(obj.image, 120))

    @admin.display(description='Aperçu')
    def apercu(self, obj):
        if obj.image:
            return format_html('<img src="{}" alt="" style="max-width:220px;max-height:220px;border-radius:12px;'
                               'background:#fff;border:1px solid #E2E8F0;padding:6px">', webp(obj.image, 480))
        return "Aucune photo : le site affiche un visuel généré (couleur de la catégorie + référence + nom)."

    def save_model(self, request, obj, form, change):
        image_importee = getattr(form, 'image_importee', None)
        nouvelle_photo = image_importee or 'image' in form.changed_data
        if nouvelle_photo and not {'credit_image', 'source_image'} & set(form.changed_data):
            # nouvelle photo sans nouveau crédit : l'ancien crédit ne la concerne plus
            obj.credit_image, obj.source_image = '', ''
        if image_importee:
            # l'ancienne photo est supprimée du disque après l'enregistrement (core/images.py)
            obj.image.save(f"{obj.slug or 'produit'}.webp", image_importee, save=False)
        super().save_model(request, obj, form, change)
        if image_importee:
            self.message_user(request, "Image importée depuis le lien et compressée en WebP.", messages.SUCCESS)

    @admin.action(description="Publier les produits sélectionnés")
    def publier(self, request, queryset):
        self.message_user(request, f"{queryset.update(actif=True)} produit(s) publié(s).", messages.SUCCESS)

    @admin.action(description="Masquer les produits sélectionnés")
    def masquer(self, request, queryset):
        self.message_user(request, f"{queryset.update(actif=False)} produit(s) masqué(s).", messages.SUCCESS)

    def get_urls(self):
        return [path('charger-catalogue/', self.admin_site.admin_view(self.charger_catalogue_view),
                     name='boutique_produit_charger_catalogue')] + super().get_urls()

    def charger_catalogue_view(self, request):
        if request.method != 'POST' or not self.has_add_permission(request):
            raise Http404
        crees, _, _, ignores = charger_catalogue(force=False)
        if crees:
            self.message_user(request, f"{crees} produit(s) ajouté(s), masqués avec un stock à 0 : ajoutez l'image et la quantité "
                                       "puis publiez ceux que vous souhaitez afficher.", messages.SUCCESS)
        else:
            self.message_user(request, "Le catalogue est déjà complet : aucun produit ajouté.", messages.INFO)
        if ignores:
            self.message_user(request, f"{ignores} composant(s) que vous aviez supprimé(s) n'ont pas été recréés "
                                       "(voir « Composants retirés du catalogue »).", messages.INFO)
        return redirect(reverse('admin:boutique_produit_changelist') + '?actif__exact=0')

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            'nb_publies': Produit.objects.filter(actif=True).count(),
            'nb_masques': Produit.objects.filter(actif=False).count(),
            'nb_sans_image': Produit.objects.filter(Q(image='') | Q(image__isnull=True)).count(),
            'nb_rupture': Produit.objects.filter(stock=0).count(),
            'catalogue_total': nombre_produits(),
        }
        return super().changelist_view(request, extra_context=extra_context)


class CommandeItemInline(admin.TabularInline):
    model = CommandeItem
    extra = 0
    readonly_fields = ['produit', 'nom_produit', 'prix_unitaire', 'quantite']


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'prenom', 'montant_total', 'statut', 'created_at']
    list_filter = ['statut']
    search_fields = ['nom', 'prenom', 'email', 'telephone']
    readonly_fields = ['created_at', 'payee_le', 'preparee_le', 'expediee_le', 'livree_le', 'annulee_le', 'fedapay_transaction_id']
    inlines = [CommandeItemInline]
    date_hierarchy = 'created_at'
    change_list_template = 'admin/boutique/commande/change_list.html'
    actions = ['marquer_en_preparation', 'marquer_expediee', 'marquer_livree']
    fieldsets = [
        ('Suivi (visible par le client)', {
            'fields': ['statut', 'message_suivi', 'payee_le', 'preparee_le', 'expediee_le', 'livree_le', 'annulee_le'],
            'description': "Changer le statut prévient le client par e-mail et met à jour sa page de suivi.",
        }),
        ('Client', {'fields': ['utilisateur', 'prenom', 'nom', 'email', 'telephone']}),
        ('Livraison', {'fields': ['adresse_livraison', 'ville', 'notes']}),
        ('Paiement', {'fields': ['montant_total', 'fedapay_transaction_id', 'created_at']}),
    ]

    def _prevenir_client(self, request, commande):
        try:
            if envoyer_email_suivi(commande, request):
                self.message_user(request, f"Commande #{commande.pk} : le client a été prévenu par e-mail.")
        except Exception as erreur:
            # avertissement (pas une erreur) : inutile de prévenir les admins… par un e-mail qui ne partirait pas
            logger.warning("E-mail de suivi impossible pour la commande #%s", commande.pk, exc_info=True)
            self.message_user(
                request,
                f"Commande #{commande.pk} : statut enregistré, mais l'e-mail au client n'a pas pu partir — {raison_echec_email(erreur)}",
                messages.WARNING,
            )

    def save_model(self, request, obj, form, change):
        statut_change = change and 'statut' in form.changed_data
        super().save_model(request, obj, form, change)
        if statut_change:
            self._prevenir_client(request, obj)

    def _changer_statut(self, request, queryset, statut):
        faites = 0
        # seulement les commandes payées : on ne fait pas avancer une commande impayée ou annulée
        for commande in queryset.exclude(statut__in=['en_attente', 'annulee', statut]):
            commande.statut = statut
            commande.save()
            self._prevenir_client(request, commande)
            faites += 1
        self.message_user(request, f"{faites} commande(s) mise(s) à jour.")

    @admin.action(description='Marquer « En préparation » (prévient le client)')
    def marquer_en_preparation(self, request, queryset):
        self._changer_statut(request, queryset, 'en_preparation')

    @admin.action(description='Marquer « Expédiée » (prévient le client)')
    def marquer_expediee(self, request, queryset):
        self._changer_statut(request, queryset, 'expediee')

    @admin.action(description='Marquer « Livrée » (prévient le client)')
    def marquer_livree(self, request, queryset):
        self._changer_statut(request, queryset, 'livree')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'report-pdf/',
                self.admin_site.admin_view(self.report_pdf_view),
                name='boutique_commande_report_pdf',
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

    def report_pdf_view(self, request):
        period = request.GET.get('period', 'day')
        start_date, period_label = self._period_config(period)

        queryset = Commande.objects.filter(
            statut='payee',
            created_at__gte=start_date,
        ).order_by('-created_at')

        total_amount = queryset.aggregate(total=Sum('montant_total')).get('total') or 0

        response = HttpResponse(content_type='application/pdf')
        safe_period = period if period in ['day', 'week', 'month', 'year'] else 'day'
        response['Content-Disposition'] = f'inline; filename="rapport-commandes-payees-{safe_period}.pdf"'

        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        margin = 32
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
            pdf.drawString(margin, height - 30, 'Rapport commandes payees')
            pdf.setFont('Helvetica', 9)
            pdf.drawString(margin, height - 46, f'KcoMat  |  Periode: {period_label}')
            pdf.drawRightString(width - margin, height - 46, f'Genere le: {now_local.strftime("%d/%m/%Y %H:%M")}')

            # Footer page number
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
                ('Commandes payees', str(queryset.count())),
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

        def draw_table_header(y_top):
            row_h = 20
            pdf.setFillColor(primary_dark)
            pdf.setStrokeColor(primary_dark)
            pdf.rect(margin, y_top - row_h, width - (margin * 2), row_h, stroke=1, fill=1)

            pdf.setFillColor(colors.white)
            pdf.setFont('Helvetica-Bold', 9)
            pdf.drawString(margin + 8, y_top - 13, 'Date')
            pdf.drawString(margin + 80, y_top - 13, 'Client')
            pdf.drawString(margin + 220, y_top - 13, 'Email')
            pdf.drawString(margin + 390, y_top - 13, 'Telephone')
            pdf.drawRightString(width - margin - 8, y_top - 13, 'Montant')
            return y_top - row_h

        page_no = 1
        draw_page_header(page_no)
        y = draw_summary_cards(height - 90)
        y = draw_table_header(y)

        row_h = 18
        toggle = False
        pdf.setFont('Helvetica', 8.5)

        if not queryset.exists():
            pdf.setFillColor(colors.HexColor('#6B7C93'))
            pdf.setFont('Helvetica-Oblique', 9)
            pdf.drawString(margin + 8, y - 18, 'Aucune commande payee sur cette periode.')
        else:
            for commande in queryset:
                if y < 72:
                    pdf.showPage()
                    page_no += 1
                    draw_page_header(page_no)
                    y = draw_table_header(height - 90)
                    toggle = False
                    pdf.setFont('Helvetica', 8.5)

                if toggle:
                    pdf.setFillColor(zebra)
                    pdf.rect(margin, y - row_h, width - (margin * 2), row_h, stroke=0, fill=1)

                pdf.setStrokeColor(border)
                pdf.rect(margin, y - row_h, width - (margin * 2), row_h, stroke=1, fill=0)

                date_text = timezone.localtime(commande.created_at).strftime('%d/%m/%Y')
                client_text = f'{commande.prenom} {commande.nom}'[:30]
                email_text = (commande.email or '')[:33]
                phone_text = (commande.telephone or '')[:16]
                amount_text = money(commande.montant_total)

                pdf.setFillColor(colors.black)
                pdf.drawString(margin + 8, y - 12, date_text)
                pdf.drawString(margin + 80, y - 12, client_text)
                pdf.drawString(margin + 220, y - 12, email_text)
                pdf.drawString(margin + 390, y - 12, phone_text)
                pdf.drawRightString(width - margin - 8, y - 12, amount_text)

                y -= row_h
                toggle = not toggle

        pdf.save()
        return response
