from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import unicodedata

from django.conf import settings
from django.http import HttpResponse

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _money(value):
    if value is None:
        value = Decimal('0')
    try:
        value = Decimal(value)
    except Exception:
        value = Decimal('0')
    return f"{int(value):,}".replace(',', ' ') + " FCFA"


def _logo_path():
    base_dir = Path(settings.BASE_DIR)
    candidates = [
        base_dir / 'Kcomat2.jpg',
        base_dir / 'static' / 'img' / 'Kcomat2.jpg',
        base_dir / 'staticfiles' / 'img' / 'Kcomat2.jpg',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _company_info():
    info = getattr(settings, 'KCOMAT_INFO', {}) or {}
    return {
        'name': info.get('name', 'KcoMat'),
        'address': info.get('address', 'Lokossa, Mono, Benin'),
        'email': info.get('email', 'kcomat0@gmail.com'),
        'phone': info.get('phone', '+229 01 96 78 00 99'),
        'ifu': info.get('ifu', ''),
        'rccm': info.get('rccm', ''),
    }


def _normalize_text(value):
    text = str(value or '').strip().lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in text)
    return ' '.join(text.split())


def build_invoice_response(
    *,
    filename,
    title,
    invoice_number,
    customer_name,
    customer_email,
    customer_phone,
    customer_address,
    status_label,
    items,
    total_amount,
    note=''
):
    """
    items: list of dicts {description, quantity, unit_price, subtotal}
    """
    footer_text = 'Cette facture est une estimation avant validation definitive de la commande. Site web: https://kcomat.com'
    footer_norm = _normalize_text(footer_text)
    clean_note = str(note or '').strip()
    note_norm = _normalize_text(clean_note)
    should_render_note = bool(
        clean_note and note_norm and note_norm not in footer_norm and footer_norm not in note_norm
    )

    thumb_size = 36
    row_h = max(22, thumb_size + 6)
    item_count = max(len(items), 1)
    base_height = 320
    estimated_height = base_height + (item_count * row_h)
    if should_render_note:
        estimated_height += 28

    page_width = A4[0]
    page_height = min(max(460, estimated_height), A4[1])

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    width, height = page_width, page_height

    company = _company_info()

    margin = 34
    content_width = width - (margin * 2)
    line_color = colors.HexColor('#D6DCE5')
    accent_color = colors.HexColor('#124076')
    soft_bg = colors.HexColor('#F4F7FC')
    y = height - 55

    def draw_footer(page_no):
        pdf.setFont('Helvetica', 8)
        pdf.setFillColor(colors.grey)
        pdf.drawCentredString(width / 2, 24, footer_text)

    page_no = 1

    # Header area: brand at left, invoice metadata card at right.
    logo = _logo_path()
    if logo:
        try:
            pdf.drawImage(ImageReader(str(logo)), margin, y - 40, width=54, height=54, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    pdf.setFillColor(accent_color)
    pdf.setFont('Helvetica-Bold', 20)
    pdf.drawString(margin + 64, y, company['name'])
    pdf.setFillColor(colors.black)
    pdf.setFont('Helvetica', 9.5)
    pdf.drawString(margin + 64, y - 14, company['address'])
    pdf.drawString(margin + 64, y - 27, f"Email: {company['email']}")
    pdf.drawString(margin + 64, y - 40, f"Tel: {company['phone']}")

    card_w = 224
    card_h = 78
    card_x = width - margin - card_w
    card_y = y - 50
    pdf.setFillColor(soft_bg)
    pdf.setStrokeColor(line_color)
    pdf.roundRect(card_x, card_y, card_w, card_h, 6, stroke=1, fill=1)
    pdf.setFillColor(accent_color)
    pdf.setFont('Helvetica-Bold', 14.5)
    pdf.drawString(card_x + 12, card_y + card_h - 21, title)
    pdf.setFillColor(colors.black)
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(card_x + 12, card_y + card_h - 38, f"No: {invoice_number}")
    pdf.setFont('Helvetica', 9.5)
    pdf.drawString(card_x + 12, card_y + card_h - 52, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    pdf.drawString(card_x + 12, card_y + card_h - 66, f"Statut: {status_label}")

    y = card_y - 12
    pdf.setStrokeColor(line_color)
    pdf.line(margin, y, width - margin, y)
    y -= 12

    # Information blocks: customer and legal identifiers.
    line_gap = 13
    customer_lines = 4
    legal_lines = 2 + int(bool(company['ifu'])) + int(bool(company['rccm']))
    max_lines = max(customer_lines, legal_lines)
    content_start_offset = 34
    bottom_padding = 14
    block_h = max(78, content_start_offset + ((max_lines - 1) * line_gap) + bottom_padding)
    left_w = (content_width * 0.61)
    right_w = content_width - left_w - 10
    left_x = margin
    right_x = left_x + left_w + 10

    pdf.setFillColor(soft_bg)
    pdf.roundRect(left_x, y - block_h, left_w, block_h, 5, stroke=1, fill=1)
    pdf.roundRect(right_x, y - block_h, right_w, block_h, 5, stroke=1, fill=1)

    pdf.setFillColor(accent_color)
    pdf.setFont('Helvetica-Bold', 10.5)
    pdf.drawString(left_x + 10, y - 18, 'FACTURER A :')
    pdf.drawString(right_x + 10, y - 18, 'INFORMATIONS LEGALES :')

    pdf.setFillColor(colors.black)
    pdf.setFont('Helvetica', 9.5)
    line_y = y - content_start_offset
    pdf.drawString(left_x + 10, line_y, f"Nom & Prenom : {customer_name or 'Client KcoMat'}")
    line_y -= line_gap
    if customer_email:
        pdf.drawString(left_x + 10, line_y, f'Email : {customer_email}')
    else:
        pdf.drawString(left_x + 10, line_y, 'Email :')
    line_y -= line_gap
    if customer_phone:
        pdf.drawString(left_x + 10, line_y, f'Telephone : {customer_phone}')
    else:
        pdf.drawString(left_x + 10, line_y, 'Telephone :')
    line_y -= line_gap
    if customer_address:
        pdf.drawString(left_x + 10, line_y, f'Adresse : {customer_address}')
    else:
        pdf.drawString(left_x + 10, line_y, 'Adresse :')

    legal_line_y = y - content_start_offset
    pdf.drawString(right_x + 10, legal_line_y, f"Entreprise : {company['name']}")
    legal_line_y -= line_gap
    if company['ifu']:
        pdf.drawString(right_x + 10, legal_line_y, f"N° IFU : {company['ifu']}")
        legal_line_y -= line_gap
    if company['rccm']:
        pdf.drawString(right_x + 10, legal_line_y, f"RCCM : {company['rccm']}")
        legal_line_y -= line_gap
    pdf.drawString(right_x + 10, legal_line_y, company['address'])

    y -= (block_h + 16)

    # Table header.
    table_x = margin
    table_w = content_width
    col_qty = table_x + (table_w * 0.54)
    col_unit = table_x + (table_w * 0.66)
    col_total = table_x + (table_w * 0.83)

    def draw_table_header(header_y):
        pdf.setFillColor(accent_color)
        pdf.setStrokeColor(accent_color)
        pdf.rect(table_x, header_y - row_h, table_w, row_h, stroke=1, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 9.8)
        header_text_y = header_y - (row_h / 2) - 3
        pdf.drawString(table_x + 8, header_text_y, 'Description')
        pdf.drawRightString(col_unit - 8, header_text_y, 'Qte')
        pdf.drawRightString(col_total - 8, header_text_y, 'PU')
        pdf.drawRightString(table_x + table_w - 8, header_text_y, 'Montant')

    draw_table_header(y)
    y -= row_h

    # Table rows.
    pdf.setFont('Helvetica', 9.5)
    pdf.setStrokeColor(line_color)
    zebra = False
    for row in items:
        if y < 122:
            draw_footer(page_no)
            pdf.showPage()
            page_no += 1
            y = height - 58
            draw_table_header(y)
            y -= row_h
            pdf.setFont('Helvetica', 9.5)
            pdf.setStrokeColor(line_color)
            zebra = False

        description = str(row.get('description', ''))
        image_path = str(row.get('image_path', '') or '').strip()
        quantity = str(row.get('quantity', 1))
        unit_price = _money(row.get('unit_price', 0))
        subtotal = _money(row.get('subtotal', 0))

        if zebra:
            pdf.setFillColor(colors.HexColor('#FAFCFF'))
            pdf.rect(table_x, y - row_h, table_w, row_h, stroke=0, fill=1)
        pdf.rect(table_x, y - row_h, table_w, row_h, stroke=1, fill=0)
        pdf.setStrokeColor(line_color)
        pdf.line(col_qty, y, col_qty, y - row_h)
        pdf.line(col_unit, y, col_unit, y - row_h)
        pdf.line(col_total, y, col_total, y - row_h)

        pdf.setFillColor(colors.black)
        text_x = table_x + 8
        if image_path:
            try:
                thumb_x = table_x + 8
                thumb_y = y - row_h + ((row_h - thumb_size) / 2)
                pdf.drawImage(
                    ImageReader(image_path),
                    thumb_x,
                    thumb_y,
                    width=thumb_size,
                    height=thumb_size,
                    preserveAspectRatio=True,
                    mask='auto',
                )
                text_x = thumb_x + thumb_size + 6
            except Exception:
                text_x = table_x + 8

        available_desc_width = max(col_qty - text_x - 8, 60)
        max_chars = max(int(available_desc_width / 4.9), 12)
        if len(description) > max_chars:
            description = description[: max_chars - 1] + '…'

        row_text_y = y - (row_h / 2) - 3
        pdf.drawString(text_x, row_text_y, description)
        pdf.drawRightString(col_unit - 8, row_text_y, quantity)
        pdf.drawRightString(col_total - 8, row_text_y, unit_price)
        pdf.drawRightString(table_x + table_w - 8, row_text_y, subtotal)

        y -= row_h
        zebra = not zebra

    y -= 12

    # Total block.
    total_box_w = 224
    total_box_h = 36
    total_x = width - margin - total_box_w
    pdf.setFillColor(soft_bg)
    pdf.setStrokeColor(line_color)
    pdf.roundRect(total_x, y - total_box_h, total_box_w, total_box_h, 5, stroke=1, fill=1)
    pdf.setFillColor(accent_color)
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(total_x + 10, y - 23, 'Total à Payer :')
    pdf.drawRightString(total_x + total_box_w - 10, y - 23, _money(total_amount))

    if should_render_note:
        y -= 44
        pdf.setFont('Helvetica-Oblique', 8.8)
        pdf.setFillColor(colors.black)
        pdf.drawString(margin, y, clean_note)

    # Footer
    draw_footer(page_no)

    pdf.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
