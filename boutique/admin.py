from django.contrib import admin
from django.db.models import Sum
from django.http import HttpResponse
from django.urls import path
from django.utils import timezone
from datetime import timedelta

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from .models import CategorieProduit, Produit, ImageProduit, Commande, CommandeItem


@admin.register(CategorieProduit)
class CategorieProduitAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'ordre']
    list_editable = ['ordre']
    prepopulated_fields = {'slug': ('nom',)}


class ImageProduitInline(admin.TabularInline):
    model = ImageProduit
    extra = 2
    fields = ['image', 'alt', 'ordre']


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ['nom', 'categorie', 'prix', 'stock', 'actif', 'en_vedette', 'nouveau']
    list_filter = ['actif', 'en_vedette', 'nouveau', 'categorie']
    list_editable = ['actif', 'en_vedette', 'prix', 'stock']
    search_fields = ['nom', 'reference', 'description']
    prepopulated_fields = {'slug': ('nom',)}
    inlines = [ImageProduitInline]


class CommandeItemInline(admin.TabularInline):
    model = CommandeItem
    extra = 0
    readonly_fields = ['produit', 'nom_produit', 'prix_unitaire', 'quantite']


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'prenom', 'montant_total', 'statut', 'created_at']
    list_filter = ['statut']
    search_fields = ['nom', 'prenom', 'email', 'telephone']
    readonly_fields = ['created_at', 'payee_le', 'fedapay_transaction_id']
    inlines = [CommandeItemInline]
    date_hierarchy = 'created_at'
    change_list_template = 'admin/boutique/commande/change_list.html'

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
