from django.contrib import admin
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.http import HttpResponse
from django.urls import path
from django.utils import timezone

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from .models import CategorieFormation, Formation, Inscription, PaiementFormation


@admin.register(CategorieFormation)
class CategorieFormationAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'couleur']
    prepopulated_fields = {'slug': ('nom',)}


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ['titre', 'categorie', 'prix', 'places_disponibles', 'actif', 'en_vedette', 'nouveau']
    list_filter = ['actif', 'en_vedette', 'nouveau', 'categorie', 'niveau']
    list_editable = ['actif', 'en_vedette', 'nouveau']
    search_fields = ['titre', 'description']
    prepopulated_fields = {'slug': ('titre',)}
    fieldsets = (
        ('Informations principales', {
            'fields': ('titre', 'slug', 'categorie', 'description_courte', 'description', 'image')
        }),
        ('Détails', {
            'fields': ('duree', 'niveau', 'prix', 'prix_avec_base', 'places_disponibles')
        }),
        ('Contenu pédagogique', {
            'fields': ('objectifs', 'prerequis')
        }),
        ('Statut et mise en avant', {
            'fields': ('actif', 'nouveau', 'en_vedette')
        }),
    )


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ['prenom', 'nom', 'email', 'formation', 'statut', 'created_at']
    list_filter = ['statut', 'formation']
    search_fields = ['nom', 'prenom', 'email', 'telephone']
    readonly_fields = ['created_at', 'frais_payes_le', 'formation_payee_le']
    date_hierarchy = 'created_at'
    list_select_related = ['formation']
    change_list_template = 'admin/formations/inscription/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'report-pdf/',
                self.admin_site.admin_view(self.report_pdf_view),
                name='formations_inscription_report_pdf',
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

    def _paid_amount_for_inscription(self, inscription):
        frais = Decimal(settings.KCOMAT_INFO.get('frais_inscription', 2000))
        formation_price = Decimal(inscription.formation.prix or 0)
        if inscription.statut == 'complet' or inscription.formation_payee_le is not None:
            return frais + formation_price
        return frais

    def report_pdf_view(self, request):
        period = request.GET.get('period', 'day')
        start_date, period_label = self._period_config(period)

        queryset = Inscription.objects.select_related('formation').filter(
            statut__in=['frais_payes', 'complet'],
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
        'message',
        'statut',
        'fedapay_frais_id',
        'frais_payes_le',
        'fedapay_formation_id',
        'formation_payee_le',
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
        return qs.filter(statut__in=['frais_payes', 'complet'])

    @admin.display(description='Montant encaissé')
    def montant_encaisse(self, obj):
        frais = Decimal(settings.KCOMAT_INFO.get('frais_inscription', 2000))
        if obj.statut == 'complet' or obj.formation_payee_le is not None:
            montant = frais + Decimal(obj.formation.prix or 0)
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
        if obj.statut == 'complet' or obj.formation_payee_le is not None:
            return frais + Decimal(obj.formation.prix or 0)
        return frais
