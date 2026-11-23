"""Attestations de formation (apprenants) et d'intervention (formateurs) : PDF, e-mail, archive ZIP."""
import logging
import zipfile
from io import BytesIO

from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.formats import date_format
from django.utils.text import slugify

from core import attestation_pdf
from core.attestation_pdf import Attestation, site_url

logger = logging.getLogger(__name__)


def _date(valeur):
    with translation.override('fr'):
        return date_format(valeur, 'j F Y')


def periode(debut, fin):
    """« le 3 novembre 2026 » ou « du 3 au 14 novembre 2026 » / « du 28 octobre au 4 novembre 2026 »."""
    if debut == fin:
        return f"le {_date(debut)}"
    if (debut.year, debut.month) == (fin.year, fin.month):
        return f"du {debut.day}{'er' if debut.day == 1 else ''} au {_date(fin)}"
    if debut.year == fin.year:
        with translation.override('fr'):
            return f"du {date_format(debut, 'j F')} au {_date(fin)}"
    return f"du {_date(debut)} au {_date(fin)}"


def _duree(formation):
    duree = (formation.duree or '').strip()
    return '' if not duree or duree.lower().startswith('à définir') else duree


def chemin_verification(objet):
    return reverse('formations:verifier_attestation', args=[objet.code_verification])


# --------------------------------------------------------------------------- apprenants
def pdf_apprenant(inscription):
    formation = inscription.formation
    formateurs = [f.nom_complet for f in formation.formateurs.all()]
    morceaux = [periode(inscription.session_debut, inscription.session_fin)]
    if _duree(formation):
        morceaux.append(f"d'une durée de {_duree(formation)}")
    morceaux.append("en ligne" if inscription.mode_preference == 'en_ligne' else "en présentiel à Lokossa")
    if formateurs:
        noms = formateurs[0] if len(formateurs) == 1 else f"{', '.join(formateurs[:-1])} et {formateurs[-1]}"
        morceaux.append(f"sous la conduite de {noms}")
    details = ", ".join(morceaux) + "."
    return attestation_pdf.generer_pdf(Attestation(
        titre="ATTESTATION DE FORMATION",
        numero=inscription.numero_attestation,
        beneficiaire=inscription.nom_complet,
        action="a suivi avec assiduité la formation",
        intitule=formation.titre,
        details=details[0].upper() + details[1:],
        fait_le=_date(inscription.session_fin),
        url_verification=site_url() + chemin_verification(inscription),
        chemin_verification=chemin_verification(inscription),
        mention_cachet='FORMATION',
    ))


def nom_fichier_apprenant(inscription):
    return f"attestation-kcomat-{slugify(inscription.formation.titre)[:40]}-{slugify(inscription.nom_complet)}.pdf"


# --------------------------------------------------------------------------- formateurs
def pdf_formateur(attestation):
    formateur, formation = attestation.formateur, attestation.formation
    morceaux = [periode(attestation.session_debut, attestation.session_fin)]
    if attestation.volume_horaire:
        morceaux.append(f"pour un volume horaire de {attestation.volume_horaire} heures")
    if attestation.nb_apprenants:
        morceaux.append(f"auprès de {attestation.nb_apprenants} apprenant{'s' if attestation.nb_apprenants > 1 else ''}")
    if formateur.fonction:
        fonction = formateur.fonction[0].lower() + formateur.fonction[1:]
        morceaux.insert(0, f"en qualité {'d’' if fonction[0] in 'aeiouyhéèêâîôû' else 'de '}{fonction}")
    details = ", ".join(morceaux) + "."
    return attestation_pdf.generer_pdf(Attestation(
        titre="ATTESTATION D'INTERVENTION",
        numero=attestation.numero_attestation,
        beneficiaire=formateur.nom_complet,
        action="a assuré l'animation de la formation",
        intitule=formation.titre,
        details=details[0].upper() + details[1:],
        fait_le=_date(attestation.delivree_le),
        url_verification=site_url() + chemin_verification(attestation),
        chemin_verification=chemin_verification(attestation),
        mention_cachet='FORMATION',
    ))


def nom_fichier_formateur(attestation):
    return (f"attestation-intervention-kcomat-{slugify(attestation.formation.titre)[:40]}-"
            f"{slugify(attestation.formateur.nom_complet)}.pdf")


# --------------------------------------------------------------------------- envoi
def _signature():
    info = settings.KCOMAT_INFO
    return f"L'équipe KcoMat\n{info['phone']} · {info['email']}\n{info['address']}"


def envoyer_apprenant(inscription):
    body = (
        f"Bonjour {inscription.prenom},\n\n"
        f"Félicitations pour avoir suivi la formation « {inscription.formation.titre} » "
        f"({periode(inscription.session_debut, inscription.session_fin)}).\n\n"
        f"Votre attestation de formation est jointe à ce message. Son authenticité peut être vérifiée à tout moment "
        f"en scannant le QR code qui y figure, ou à cette adresse :\n{site_url()}{chemin_verification(inscription)}\n\n"
        f"Merci pour votre confiance et à bientôt pour une nouvelle formation,\n{_signature()}"
    )
    message = EmailMessage(subject=f"KcoMat — Votre attestation : {inscription.formation.titre}", body=body,
                           to=[inscription.email], reply_to=[settings.KCOMAT_INFO['email']])
    message.attach(nom_fichier_apprenant(inscription), pdf_apprenant(inscription), 'application/pdf')
    message.send(fail_silently=False)
    type(inscription).objects.filter(pk=inscription.pk).update(attestation_envoyee_le=timezone.now())


def envoyer_formateur(attestation):
    formateur = attestation.formateur
    body = (
        f"Bonjour {formateur.prenom},\n\n"
        f"Merci d'avoir animé la formation « {attestation.formation.titre} » "
        f"({periode(attestation.session_debut, attestation.session_fin)}).\n\n"
        f"Vous trouverez ci-joint votre attestation d'intervention. Elle est vérifiable à cette adresse :\n"
        f"{site_url()}{chemin_verification(attestation)}\n\n"
        f"Bien cordialement,\n{_signature()}"
    )
    message = EmailMessage(subject=f"KcoMat — Attestation d'intervention : {attestation.formation.titre}", body=body,
                           to=[formateur.email], reply_to=[settings.KCOMAT_INFO['email']])
    message.attach(nom_fichier_formateur(attestation), pdf_formateur(attestation), 'application/pdf')
    message.send(fail_silently=False)
    type(attestation).objects.filter(pk=attestation.pk).update(envoyee_le=timezone.now())


def envoyer_lot(objets, envoyer):
    """Envoie chaque attestation ; renvoie (envoyées, adresses en échec)."""
    envoyees, echecs = 0, []
    for objet in objets:
        try:
            envoyer(objet)
            envoyees += 1
        except Exception:
            adresse = getattr(objet, 'email', '') or objet.formateur.email
            logger.exception("Attestation non envoyée à %s", adresse)
            echecs.append(adresse)
    return envoyees, echecs


# --------------------------------------------------------------------------- réponses HTTP
def reponse_pdf(contenu, nom):
    return attestation_pdf.reponse_pdf(contenu, nom)


def reponse_zip(fichiers, nom_archive):
    """fichiers : [(nom, contenu PDF)]"""
    tampon = BytesIO()
    with zipfile.ZipFile(tampon, 'w', zipfile.ZIP_DEFLATED) as archive:
        noms = set()
        for nom, contenu in fichiers:
            base, n = nom, 2
            while nom in noms:                       # homonymes : suffixe -2, -3…
                nom = base.replace('.pdf', f'-{n}.pdf')
                n += 1
            noms.add(nom)
            archive.writestr(nom, contenu)
    response = HttpResponse(tampon.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{nom_archive}.zip"'
    return response
