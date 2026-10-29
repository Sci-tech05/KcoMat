"""Attestation de participation (PDF A4 paysage) : participant, webinaire, entreprise, QR de vérification."""
from io import BytesIO

from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.formats import date_format
from django.utils.text import slugify
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

from core.pdf_invoices import _company_info, _logo_path

NAVY = colors.HexColor('#0B1F4D')
BLEU = colors.HexColor('#0A84FF')
CYAN = colors.HexColor('#22D3EE')
OR = colors.HexColor('#C9A227')
GRIS = colors.HexColor('#5B6475')
FILET = colors.HexColor('#D6DCE5')


def _site_url():
    from django.conf import settings
    return (getattr(settings, 'FEDAPAY_APP_URL', '') or 'https://kcomat0.pythonanywhere.com').rstrip('/')


def url_verification(participation):
    return _site_url() + reverse('webinaires:verifier', args=[participation.code_verification])


def _texte_centre(pdf, texte, x, y, police, taille, largeur_max, interligne=None):
    """Texte centré sur plusieurs lignes si besoin ; renvoie le y sous le bloc."""
    lignes = simpleSplit(texte, police, taille, largeur_max)
    pdf.setFont(police, taille)
    for ligne in lignes:
        pdf.drawCentredString(x, y, ligne)
        y -= interligne or taille * 1.25
    return y


def _qr(pdf, donnees, x, y, taille):
    widget = QrCodeWidget(donnees)
    widget.barFillColor = NAVY
    x0, y0, x1, y1 = widget.getBounds()
    dessin = Drawing(taille, taille, transform=[taille / (x1 - x0), 0, 0, taille / (y1 - y0), 0, 0])
    dessin.add(widget)
    renderPDF.draw(dessin, pdf, x, y)


def _cachet(pdf, cx, cy, nom):
    """Cachet circulaire stylisé de l'entreprise."""
    pdf.saveState()
    pdf.setStrokeColor(BLEU)
    pdf.setFillColor(BLEU)
    pdf.setLineWidth(1.6)
    pdf.circle(cx, cy, 38, stroke=1, fill=0)
    pdf.setLineWidth(0.7)
    pdf.circle(cx, cy, 32, stroke=1, fill=0)
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawCentredString(cx, cy + 2, nom.upper())
    pdf.setFont('Helvetica', 6.2)
    pdf.drawCentredString(cx, cy - 8, 'LOKOSSA · BÉNIN')
    pdf.setFont('Helvetica-Bold', 5.6)
    pdf.drawCentredString(cx, cy + 17, '★ CERTIFIÉ ★')
    pdf.drawCentredString(cx, cy - 21, 'WEBINAIRE')
    pdf.restoreState()


def generer_pdf(participation):
    webinaire = participation.webinaire
    entreprise = _company_info()
    largeur, hauteur = landscape(A4)
    tampon = BytesIO()
    pdf = canvas.Canvas(tampon, pagesize=(largeur, hauteur))
    pdf.setTitle(f"Attestation de participation — {participation.nom_complet}")
    pdf.setAuthor(entreprise['name'])
    pdf.setSubject(webinaire.titre)

    # Fond et encadrements
    pdf.setFillColor(colors.HexColor('#FBFCFF'))
    pdf.rect(0, 0, largeur, hauteur, stroke=0, fill=1)
    pdf.setFillColor(NAVY)
    pdf.rect(0, hauteur - 14, largeur, 14, stroke=0, fill=1)
    pdf.rect(0, 0, largeur, 14, stroke=0, fill=1)
    pdf.setFillColor(CYAN)
    pdf.rect(0, hauteur - 18, largeur * 0.42, 4, stroke=0, fill=1)
    pdf.setFillColor(BLEU)
    pdf.rect(largeur * 0.58, 14, largeur * 0.42, 4, stroke=0, fill=1)
    pdf.setStrokeColor(OR)
    pdf.setLineWidth(1.2)
    pdf.roundRect(30, 34, largeur - 60, hauteur - 68, 10, stroke=1, fill=0)
    pdf.setStrokeColor(FILET)
    pdf.setLineWidth(0.6)
    pdf.roundRect(37, 41, largeur - 74, hauteur - 82, 7, stroke=1, fill=0)

    # Filigrane
    pdf.saveState()
    pdf.setFillColor(colors.HexColor('#EEF3FB'))
    pdf.setFont('Helvetica-Bold', 120)
    pdf.translate(largeur / 2, hauteur / 2 - 30)
    pdf.rotate(18)
    pdf.drawCentredString(0, 0, entreprise['name'].upper())
    pdf.restoreState()

    # En-tête : logo + entreprise / numéro
    haut = hauteur - 62
    logo = _logo_path()
    if logo:
        try:
            pdf.drawImage(ImageReader(str(logo)), 58, haut - 40, width=50, height=50, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    pdf.setFillColor(NAVY)
    pdf.setFont('Helvetica-Bold', 17)
    pdf.drawString(118, haut - 8, entreprise['name'])
    pdf.setFillColor(GRIS)
    pdf.setFont('Helvetica', 8.5)
    pdf.drawString(118, haut - 21, "Formations · Composants électroniques · Solutions technologiques")
    pdf.drawString(118, haut - 32, entreprise['address'])

    pdf.setFont('Helvetica', 8.5)
    pdf.drawRightString(largeur - 58, haut - 8, "Attestation N°")
    pdf.setFillColor(NAVY)
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawRightString(largeur - 58, haut - 22, participation.numero_attestation)

    # Titre
    centre = largeur / 2
    y = hauteur - 150
    pdf.setFillColor(NAVY)
    pdf.setFont('Helvetica-Bold', 30)
    pdf.drawCentredString(centre, y, "ATTESTATION DE PARTICIPATION")
    pdf.setStrokeColor(OR)
    pdf.setLineWidth(1.4)
    pdf.line(centre - 70, y - 13, centre + 70, y - 13)
    pdf.setFillColor(OR)
    pdf.circle(centre, y - 13, 2.6, stroke=0, fill=1)

    with translation.override('fr'):
        debut = timezone.localtime(webinaire.date_debut)
        fin = timezone.localtime(webinaire.date_fin)
        jour = date_format(debut, 'l j F Y')
        emis = date_format(timezone.localtime(fin), 'j F Y')

    y -= 46
    pdf.setFillColor(GRIS)
    pdf.setFont('Helvetica', 12)
    pdf.drawCentredString(centre, y, f"La société {entreprise['name']} atteste que")

    y -= 40
    pdf.setFillColor(NAVY)
    y = _texte_centre(pdf, participation.nom_complet.upper(), centre, y, 'Helvetica-Bold', 28, largeur - 200)
    pdf.setStrokeColor(FILET)
    pdf.setLineWidth(0.8)
    pdf.line(centre - 180, y + 18, centre + 180, y + 18)

    y -= 8
    pdf.setFillColor(GRIS)
    pdf.setFont('Helvetica', 12)
    pdf.drawCentredString(centre, y, "a pris part au webinaire")
    y -= 28
    pdf.setFillColor(BLEU)
    y = _texte_centre(pdf, f"« {webinaire.titre} »", centre, y, 'Helvetica-Bold', 18, largeur - 220, 23)

    y -= 6
    pdf.setFillColor(colors.HexColor('#334155'))
    details = (f"animé par {webinaire.intervenant}"
               + (f" ({webinaire.intervenant_fonction})" if webinaire.intervenant_fonction else '')
               + f", le {jour} de {debut:%H:%M} à {fin:%H:%M} (durée : {webinaire.duree}),"
               " en ligne sur la plateforme de visioconférence KcoMat.")
    _texte_centre(pdf, details, centre, y, 'Helvetica', 11, largeur - 260, 15)

    # Bas : QR de vérification | lieu et date | signature + cachet
    bas = 66
    _qr(pdf, url_verification(participation), 60, bas, 74)
    pdf.setFillColor(GRIS)
    pdf.setFont('Helvetica', 7.5)
    pdf.drawString(142, bas + 54, "Authenticité vérifiable en scannant")
    pdf.drawString(142, bas + 44, "le QR code, ou sur :")
    pdf.setFillColor(NAVY)
    pdf.setFont('Helvetica-Bold', 7.5)
    pdf.drawString(142, bas + 31, _site_url().replace('https://', ''))
    pdf.drawString(142, bas + 20, reverse('webinaires:verifier', args=[participation.code_verification]))

    pdf.setFillColor(colors.HexColor('#334155'))
    pdf.setFont('Helvetica-Oblique', 10.5)
    pdf.drawCentredString(centre, bas + 112, f"Fait à Lokossa, le {emis}")

    signature_x = largeur - 175
    _cachet(pdf, signature_x - 62, bas + 36, entreprise['name'])
    pdf.setFillColor(NAVY)
    pdf.setFont('Helvetica-Bold', 10.5)
    pdf.drawCentredString(signature_x + 30, bas + 56, f"Pour {entreprise['name']}")
    pdf.setFont('Helvetica', 9)
    pdf.setFillColor(GRIS)
    pdf.drawCentredString(signature_x + 30, bas + 43, "La Direction")
    pdf.setStrokeColor(NAVY)
    pdf.setLineWidth(0.8)
    pdf.line(signature_x - 20, bas + 18, signature_x + 80, bas + 18)

    # Pied de page légal
    legal = [entreprise['name']]
    if entreprise['ifu']:
        legal.append(f"IFU : {entreprise['ifu']}")
    if entreprise['rccm']:
        legal.append(f"RCCM : {entreprise['rccm']}")
    legal += [entreprise['phone'], entreprise['email'], _site_url().replace('https://', '')]
    pdf.setFillColor(GRIS)
    pdf.setFont('Helvetica', 7.5)
    pdf.drawCentredString(centre, 46, '  ·  '.join(legal))

    pdf.showPage()
    pdf.save()
    return tampon.getvalue()


def nom_fichier(participation):
    return f"attestation-kcomat-{slugify(participation.webinaire.titre)[:40]}-{slugify(participation.nom_complet)}.pdf"


def reponse_pdf(participation, telechargement=True):
    response = HttpResponse(generer_pdf(participation), content_type='application/pdf')
    mode = 'attachment' if telechargement else 'inline'
    response['Content-Disposition'] = f'{mode}; filename="{nom_fichier(participation)}"'
    return response
