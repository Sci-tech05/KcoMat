"""Attestation de participation à un webinaire (gabarit commun : core.attestation_pdf)."""
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.formats import date_format
from django.utils.text import slugify

from core import attestation_pdf
from core.attestation_pdf import Attestation, site_url


def url_verification(participation):
    return site_url() + reverse('webinaires:verifier', args=[participation.code_verification])


def generer_pdf(participation):
    webinaire = participation.webinaire
    with translation.override('fr'):
        jour = date_format(timezone.localtime(webinaire.date_debut), 'l j F Y')
        emis = date_format(timezone.localtime(webinaire.date_fin), 'j F Y')
    details = (f"animé par {webinaire.intervenant}"
               + (f" ({webinaire.intervenant_fonction})" if webinaire.intervenant_fonction else '')
               + f", le {jour},"
               " en ligne sur la plateforme de visioconférence KcoMat.")
    return attestation_pdf.generer_pdf(Attestation(
        titre="ATTESTATION DE PARTICIPATION",
        numero=participation.numero_attestation,
        beneficiaire=participation.nom_complet,
        action="a pris part au webinaire",
        intitule=webinaire.titre,
        details=details,
        fait_le=emis,
        url_verification=url_verification(participation),
        chemin_verification=reverse('webinaires:verifier', args=[participation.code_verification]),
        mention_cachet='WEBINAIRE',
    ))


def nom_fichier(participation):
    return f"attestation-kcomat-{slugify(participation.webinaire.titre)[:40]}-{slugify(participation.nom_complet)}.pdf"


def reponse_pdf(participation, telechargement=True):
    return attestation_pdf.reponse_pdf(generer_pdf(participation), nom_fichier(participation), telechargement)
