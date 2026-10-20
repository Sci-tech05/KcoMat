"""Exports admin des candidatures : ZIP des dossiers et rapport PDF."""
import csv
import io
import zipfile

from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .notifications import document_filename

INK = colors.HexColor('#0B1220')
BLUE = colors.HexColor('#2563EB')
MUTED = colors.HexColor('#64748B')
LINE = colors.HexColor('#E5E9F2')
STATUT_COLORS = {
    'nouvelle': '#0EA5E9', 'en_revue': '#6366F1', 'preselectionnee': '#8B5CF6',
    'entretien': '#F59E0B', 'retenue': '#10B981', 'refusee': '#F43F5E',
}


def zip_dossiers(candidatures, nom_archive):
    """ZIP : un dossier par statut, CV + lettre de chaque candidat, et un index CSV."""
    buffer = io.BytesIO()
    manquants = []
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        index = io.StringIO()
        writer = csv.writer(index, delimiter=';')
        writer.writerow(['Statut', 'Nom', 'Prénom', 'Offre', 'Type', 'Formule', 'Potentiel (/5)', 'Pré-score (/100)',
                         'E-mail', 'Téléphone', 'Reçue le'])
        for c in candidatures:
            dossier = f"{c.get_statut_display()}/{slugify(c.nom_complet)}_{slugify(c.offre.titre)[:40]}"
            for field, kind in ((c.cv, 'cv'), (c.lettre_motivation, 'lettre')):
                if not field:
                    continue
                try:
                    with field.open('rb') as fh:
                        archive.writestr(f"{dossier}/{document_filename(c, kind, field.name)}", fh.read())
                except (FileNotFoundError, OSError, ValueError):
                    manquants.append(f"{c.nom_complet} ({kind})")
            writer.writerow([c.get_statut_display(), c.nom, c.prenom, c.offre.titre, c.offre.get_type_offre_display(),
                             str(c.formule or ''),
                             c.note or '', c.score_auto, c.email, c.telephone,
                             timezone.localtime(c.created_at).strftime('%d/%m/%Y %H:%M')])
        archive.writestr('index_candidatures.csv', '﻿' + index.getvalue())  # BOM : accents OK dans Excel
        if manquants:
            archive.writestr('FICHIERS_MANQUANTS.txt', 'Fichiers introuvables sur le serveur :\n' + '\n'.join(manquants))
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{nom_archive}.zip"'
    return response


def rapport_pdf(candidatures, titre, sous_titre, nom_fichier):
    """Rapport PDF paysage : synthèse par statut puis tableau des candidats."""
    candidatures = list(candidatures)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title=titre, author='KcoMat')
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('h1', parent=styles['Title'], alignment=0, textColor=INK, fontSize=20, spaceAfter=2)
    small = ParagraphStyle('small', parent=styles['Normal'], textColor=MUTED, fontSize=9)
    cell = ParagraphStyle('cell', parent=styles['Normal'], fontSize=8.5, leading=10.5, textColor=INK)

    story = [Paragraph(titre, h1), Paragraph(sous_titre, small), Spacer(1, 6 * mm)]

    # Synthèse
    from .models import Candidature
    compte = {code: 0 for code, _ in Candidature.STATUT_CHOICES}
    for c in candidatures:
        compte[c.statut] += 1
    notes = [c.note for c in candidatures if c.note]
    synthese = [[f"{len(candidatures)}\nCandidatures"]
                + [f"{compte[code]}\n{label}" for code, label in Candidature.STATUT_CHOICES]
                + [f"{(sum(c.score_auto for c in candidatures) / len(candidatures)):.0f}/100\nPré-score moyen" if candidatures else "-\nPré-score moyen",
                   f"{(sum(notes) / len(notes)):.1f}/5\nPotentiel moyen" if notes else "-\nPotentiel moyen"]]
    synth_table = Table(synthese, colWidths=[(landscape(A4)[0] - 28 * mm) / len(synthese[0])] * len(synthese[0]))
    synth_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica-Bold', 10), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TEXTCOLOR', (0, 0), (-1, -1), INK),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F8FD')), ('BOX', (0, 0), (-1, -1), 0.6, LINE),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.white), ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7), ('BACKGROUND', (0, 0), (0, 0), BLUE),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
    ]))
    story += [synth_table, Spacer(1, 7 * mm)]

    # Tableau
    header = ['Candidat', 'Offre', 'Type', 'Statut', 'Potentiel', 'Pré-score', 'Contact', 'Reçue le']
    rows = [header]
    for c in candidatures:
        rows.append([
            Paragraph(f"<b>{c.nom_complet}</b>", cell),
            Paragraph(c.offre.titre, cell),
            c.offre.get_type_offre_display(),
            Paragraph(f'<font color="{STATUT_COLORS.get(c.statut, "#334155")}"><b>{c.get_statut_display()}</b></font>', cell),
            f"{c.note}/5" if c.note else '—',
            f"{c.score_auto}/100",
            Paragraph(f"{c.email}<br/>{c.telephone}", cell),
            timezone.localtime(c.created_at).strftime('%d/%m/%Y'),
        ])
    if len(rows) == 1:
        rows.append(['Aucune candidature sur cette période.', '', '', '', '', '', '', ''])
    widths = [48, 62, 20, 28, 20, 20, 52, 22]
    table = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1)
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8.5), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 0), (-1, 0), INK), ('FONT', (0, 1), (-1, -1), 'Helvetica', 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, LINE), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(table)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(14 * mm, 8 * mm, f"KcoMat — Rapport candidatures — généré le {timezone.localtime():%d/%m/%Y à %H:%M}")
        canvas.drawRightString(landscape(A4)[0] - 14 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier}.pdf"'
    return response
