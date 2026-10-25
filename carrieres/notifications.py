"""E-mails liés aux candidatures : alerte équipe, accusé de réception, réponse."""
import logging
import mimetypes
import os

from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024  # au-delà, on n'attache pas (limite Gmail 25 Mo au total)


def _site_url():
    return (getattr(settings, 'FEDAPAY_APP_URL', '') or '').rstrip('/')


def document_filename(candidature, kind, original_name):
    extension = os.path.splitext(original_name or '')[1].lower() or '.pdf'
    base = f"{candidature.nom}_{candidature.prenom}".upper().replace(' ', '-')
    label = 'CV' if kind == 'cv' else 'Lettre'
    return f"{label}_{base}{extension}"


def _attach(message, candidature, field, kind):
    if not field:
        return
    try:
        if field.size > MAX_ATTACHMENT_BYTES:
            return
        with field.open('rb') as fh:
            content = fh.read()
        filename = document_filename(candidature, kind, field.name)
        message.attach(filename, content, mimetypes.guess_type(filename)[0] or 'application/octet-stream')
    except Exception:
        logger.warning("Pièce jointe impossible (%s) pour la candidature #%s", kind, candidature.pk, exc_info=True)


def notifier_equipe(candidature):
    """Alerte kcomat0@gmail.com (KCOMAT_INFO['email']) dès qu'une candidature arrive."""
    offre = candidature.offre
    admin_url = _site_url() + reverse('admin:carrieres_candidature_change', args=[candidature.pk])
    lignes_score = '\n'.join(
        f"  {'✓' if points == maximum else '·'} {libelle} : {points}/{maximum}"
        for libelle, points, maximum in candidature.score_details()
    )
    body = (
        f"Nouvelle candidature reçue sur le site KcoMat.\n\n"
        f"Offre      : {offre.titre} ({offre.get_type_offre_display()})\n"
        f"Formule    : {candidature.formule or '—'}\n"
        f"Candidat   : {candidature.nom_complet}\n"
        f"E-mail     : {candidature.email}\n"
        f"Téléphone  : {candidature.telephone}\n"
        f"Reçue le   : {timezone.localtime(candidature.created_at):%d/%m/%Y à %H:%M}\n\n"
        f"Pré-score automatique : {candidature.score_auto}/100\n{lignes_score}\n\n"
        f"Motivation :\n{(candidature.message or '(non renseignée)').strip()}\n\n"
        f"Ouvrir la fiche dans l'administration :\n{admin_url}\n"
    )
    message = EmailMessage(
        subject=f"[KcoMat] Candidature {offre.get_type_offre_display().lower()} : {candidature.nom_complet} — {offre.titre}",
        body=body,
        to=[settings.KCOMAT_INFO['email']],
        reply_to=[candidature.email],
    )
    _attach(message, candidature, candidature.cv, 'cv')
    _attach(message, candidature, candidature.lettre_motivation, 'lettre')
    message.send(fail_silently=False)


def accuser_reception(candidature):
    """Confirme au candidat que son dossier a bien été reçu."""
    offre = candidature.offre
    body = (
        f"Bonjour {candidature.prenom},\n\n"
        f"Nous avons bien reçu votre candidature pour « {offre.titre} » "
        f"({offre.get_type_offre_display().lower()}). Merci de l'intérêt que vous portez à KcoMat.\n\n"
        f"Notre équipe étudie chaque dossier avec attention. Si votre profil est retenu pour la suite, "
        f"nous vous contacterons par e-mail ou par téléphone.\n\n"
        f"À bientôt,\nL'équipe KcoMat — {settings.KCOMAT_INFO['address']}\n{settings.KCOMAT_INFO['phone']}"
    )
    EmailMessage(
        subject=f"KcoMat — Candidature bien reçue : {offre.titre}",
        body=body,
        to=[candidature.email],
        reply_to=[settings.KCOMAT_INFO['email']],
    ).send(fail_silently=False)


REPONSES = {
    'entretien': (
        "Invitation à un entretien",
        "Votre candidature a retenu notre attention et nous souhaitons vous rencontrer. "
        "Un membre de l'équipe vous contactera très prochainement pour fixer la date et l'heure de l'entretien.",
    ),
    'retenue': (
        "Votre candidature est retenue",
        "Nous avons le plaisir de vous annoncer que votre candidature est retenue. "
        "Nous vous contacterons rapidement pour les prochaines étapes.",
    ),
    'refusee': (
        "Réponse à votre candidature",
        "Après étude attentive de votre dossier, nous ne sommes pas en mesure de donner une suite favorable "
        "à votre candidature pour ce poste. Nous conservons vos coordonnées et vous encourageons à postuler "
        "à nos prochaines offres.",
    ),
}


def envoyer_reponse(candidature):
    """Envoie la réponse correspondant au statut (entretien / retenue / refusée). Retourne True si envoyée."""
    if candidature.statut not in REPONSES:
        return False
    sujet, texte = REPONSES[candidature.statut]
    notes = (candidature.notes_internes or '').strip()
    if candidature.statut == candidature.STATUT_ENTRETIEN and notes:
        # Le message saisi dans « Notes internes » (date, heure, lieu…) remplace la suite du texte type
        texte = f"Votre candidature a retenu notre attention et nous souhaitons vous rencontrer en entretien.\n\n{notes}"
    body = (
        f"Bonjour {candidature.prenom},\n\n"
        f"Merci pour votre candidature au poste « {candidature.offre.titre} ».\n\n{texte}\n\n"
        f"Cordialement,\nL'équipe KcoMat\n{settings.KCOMAT_INFO['phone']} · {settings.KCOMAT_INFO['email']}"
    )
    EmailMessage(
        subject=f"KcoMat — {sujet}",
        body=body,
        to=[candidature.email],
        reply_to=[settings.KCOMAT_INFO['email']],
    ).send(fail_silently=False)
    candidature.reponse_envoyee_le = timezone.now()
    candidature.save(update_fields=['reponse_envoyee_le'])
    return True
