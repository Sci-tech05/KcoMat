"""Relances automatiques par e-mail des paiements en attente.

- Tous les 3 jours : frais d'inscription et prix des formations (y compris le solde), commandes de la
  boutique (paiement ou solde), consultation de l'accompagnement de projet, frais de stage.
- Toutes les semaines : attestations payantes des webinaires.

Chaque relance contient un lien direct vers le paiement (signé pour les personnes sans compte).
Les relances d'une étape s'arrêtent après RELANCES_MAX envois (≈ un mois), et ne partent jamais pour
une étape plus ancienne que cette fenêtre : pas de rafale sur les vieilles commandes abandonnées.

Déclenchement : au fil des visites (au plus une fois par heure, en tâche de fond) et par la commande
`python manage.py envoyer_relances_paiement` (tâche planifiée quotidienne).
"""
import logging
import threading
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.db import close_old_connections, models
from django.urls import reverse
from django.utils import timezone

from . import tranches

logger = logging.getLogger(__name__)

TOUS_LES_3_JOURS = timedelta(days=3)
CHAQUE_SEMAINE = timedelta(days=7)
RELANCES_MAX = {TOUS_LES_3_JOURS: 10, CHAQUE_SEMAINE: 4}

CLE_VERIFICATION = 'kcomat:relances-paiement'
INTERVALLE_VERIFICATION = 3600   # secondes entre deux passages déclenchés par les visites


class RelancePaiementMixin(models.Model):
    """Compteur et date de la dernière relance de paiement (par étape de paiement)."""
    relances_paiement = models.PositiveSmallIntegerField("Relances de paiement", default=0, editable=False)
    derniere_relance_le = models.DateTimeField("Dernière relance de paiement", null=True, blank=True, editable=False)

    class Meta:
        abstract = True


@dataclass
class Relance:
    objet: models.Model
    email: str
    prenom: str
    sujet: str
    texte: str
    lien: str
    depuis: object                 # début de l'étape de paiement en attente
    intervalle: timedelta = TOUS_LES_3_JOURS


def _site():
    from .attestation_pdf import site_url
    return site_url()


def _lien_signe(nom_url, objet, *args):
    from .acces import avec_jeton
    return avec_jeton(_site() + reverse(nom_url, args=args or [objet.pk]), objet)


# --------------------------------------------------------------------------- sources
def _formations(debut_fenetre):
    from formations.models import Inscription
    for i in (Inscription.objects.select_related('formation').exclude(email='')
              .filter(statut__in=['en_attente', 'frais_payes', 'acompte'], created_at__gte=debut_fenetre - timedelta(days=365))):
        titre = i.formation.titre
        if i.statut == 'en_attente':
            yield Relance(i, i.email, i.prenom, f"Finalisez votre inscription : {titre}",
                          f"Votre inscription à la formation « {titre} » attend le paiement des frais d'inscription "
                          f"({tranches.fcfa(settings.KCOMAT_INFO['frais_inscription'])}). Elle sera confirmée dès ce règlement.",
                          _lien_signe('formations:paiement_frais', i), i.created_at)
        elif i.statut == 'frais_payes':
            yield Relance(i, i.email, i.prenom, f"Réglez votre formation : {titre}",
                          f"Vos frais d'inscription à « {titre} » sont bien reçus. Il reste à régler la formation "
                          f"({tranches.fcfa(i.prix_formation)}), en une fois ou en 2 tranches de 50 %.",
                          _lien_signe('formations:paiement_formation', i), i.frais_payes_le or i.created_at)
        else:
            yield Relance(i, i.email, i.prenom, f"Solde de votre formation : {titre}",
                          f"Merci pour la 1re tranche de la formation « {titre} ». Il reste "
                          f"{tranches.fcfa(i.reste_formation)} à régler ; votre attestation sera délivrée une fois "
                          "le solde payé.",
                          _lien_signe('formations:paiement_formation', i), i.acompte_paye_le or i.created_at)


def _boutique(debut_fenetre):
    from boutique.models import Commande
    for c in (Commande.objects.exclude(email='').exclude(statut='annulee')
              .filter(created_at__gte=debut_fenetre - timedelta(days=365))):
        if c.statut == 'en_attente':
            yield Relance(c, c.email, c.prenom, f"Votre commande #{c.pk} attend son paiement",
                          f"Votre commande #{c.pk} ({tranches.fcfa(c.montant_total)}) est en attente de paiement"
                          + (f" : 1re tranche de {tranches.fcfa(c.montant_premier_paiement)}" if c.en_deux_tranches else "")
                          + ". Elle sera préparée dès réception du paiement.",
                          _lien_signe('boutique:paiement', c), c.created_at)
        elif c.premier_paiement_recu and c.reste_a_payer:
            yield Relance(c, c.email, c.prenom, f"Solde de votre commande #{c.pk}",
                          f"Merci pour la 1re tranche de votre commande #{c.pk}. Il reste {tranches.fcfa(c.reste_a_payer)} "
                          "à régler : votre colis est expédié dès réception du solde.",
                          _lien_signe('boutique:paiement_solde', c), c.payee_le)


def _accompagnement(debut_fenetre):
    from services.models import ACCOMPAGNEMENT_SLUG, FRAIS_CONSULTATION, DemandeService
    for d in DemandeService.objects.filter(service__slug=ACCOMPAGNEMENT_SLUG, consultation_payee_le__isnull=True,
                                           created_at__gte=debut_fenetre).exclude(email=''):
        yield Relance(d, d.email, d.nom, f"Votre projet « {d.intitule_projet} » : consultation à régler",
                      f"Votre demande d'accompagnement pour « {d.intitule_projet} » sera transmise à notre équipe dès "
                      f"le règlement de la session de consultation ({tranches.fcfa(FRAIS_CONSULTATION)}).",
                      _lien_signe('services:paiement_consultation', d), d.created_at)


def _stages(debut_fenetre):
    from carrieres.models import Candidature
    from carrieres.paiement import url_paiement
    for c in (Candidature.objects.select_related('offre', 'formule')
              .filter(statut=Candidature.STATUT_RETENUE, offre__nature_montant='frais').exclude(email='')):
        if not c.paiement_ouvert or not c.reste_a_payer:
            continue
        if c.tranche1_payee_le is None:
            texte = (f"Votre candidature pour « {c.offre.titre} » est retenue. Pour confirmer votre place, réglez les "
                     f"frais de stage ({tranches.fcfa(c.frais_a_payer)}), en une fois ou en 2 tranches de 50 %.")
            depuis = c.statut_modifie_le or c.created_at
        else:
            texte = (f"Merci pour la 1re tranche des frais de stage « {c.offre.titre} ». Il reste "
                     f"{tranches.fcfa(c.reste_a_payer)} à régler avant le début du stage.")
            depuis = c.tranche1_payee_le
        yield Relance(c, c.email, c.prenom, f"Frais de stage : {c.offre.titre}", texte, url_paiement(c), depuis)


def _attestations(debut_fenetre):
    from webinaires.models import ParticipationWebinaire
    for p in (ParticipationWebinaire.objects.select_related('webinaire')
              .filter(webinaire__prix_attestation__gt=0, attestation_payee_le__isnull=True,
                      rejoint_le__isnull=False, webinaire__date_fin__lte=timezone.now(),
                      webinaire__date_fin__gte=debut_fenetre).exclude(email='')):
        w = p.webinaire
        yield Relance(p, p.email, p.prenom, f"Votre attestation : {w.titre}",
                      f"Merci d'avoir participé au webinaire « {w.titre} ». Votre attestation nominative (vérifiable par "
                      f"QR code) vous attend : réglez {tranches.fcfa(p.montant_attestation_du)} pour la recevoir.",
                      _site() + reverse('webinaires:paiement_attestation', args=[w.slug]), w.date_fin, CHAQUE_SEMAINE)


SOURCES = [_formations, _boutique, _accompagnement, _stages, _attestations]


# --------------------------------------------------------------------------- envoi
def _envoyer(relance):
    corps = (f"Bonjour {relance.prenom},\n\n{relance.texte}\n\n"
             f"Payer en ligne (MTN, Moov Money), en toute sécurité via FedaPay :\n{relance.lien}\n\n"
             "Vous avez déjà réglé, ou vous ne souhaitez pas poursuivre ? Répondez simplement à ce message.\n\n"
             f"L'équipe KcoMat\n{settings.KCOMAT_INFO['phone']} · {settings.KCOMAT_INFO['email']}")
    EmailMessage(subject=f"KcoMat — Rappel : {relance.sujet}", body=corps, to=[relance.email],
                 reply_to=[settings.KCOMAT_INFO['email']]).send(fail_silently=False)


def _reserver(relance, maintenant):
    """Vérifie l'échéance et la réserve (une seule fois, même si plusieurs processus passent ensemble).
    Renvoie True si la relance doit partir maintenant."""
    objet, depuis = relance.objet, relance.depuis
    if depuis is None:
        return False
    maximum = RELANCES_MAX[relance.intervalle]
    if depuis < maintenant - relance.intervalle * maximum:
        return False                                     # étape trop ancienne : fenêtre de relance écoulée
    derniere = objet.derniere_relance_le
    # compteur de l'étape en cours : une relance antérieure à l'étape (ex. avant un 1er paiement) ne compte pas
    deja = objet.relances_paiement if derniere and derniere >= depuis else 0
    if deja >= maximum or max(derniere or depuis, depuis) > maintenant - relance.intervalle:
        return False
    filtre = {'derniere_relance_le__isnull': True} if derniere is None else {'derniere_relance_le': derniere}
    return bool(type(objet)._default_manager.filter(pk=objet.pk, **filtre)
                .update(derniere_relance_le=maintenant, relances_paiement=deja + 1))


def envoyer_relances(maintenant=None):
    """Envoie les relances arrivées à échéance ; renvoie le nombre d'e-mails envoyés."""
    maintenant = maintenant or timezone.now()
    debut_fenetre = maintenant - TOUS_LES_3_JOURS * RELANCES_MAX[TOUS_LES_3_JOURS]
    envoyees = 0
    for source in SOURCES:
        try:
            relances = list(source(debut_fenetre))
        except Exception:
            logger.exception("Relances de paiement : source %s illisible", source.__name__)
            continue
        for relance in relances:
            if not _reserver(relance, maintenant):
                continue
            try:
                _envoyer(relance)
                envoyees += 1
            except Exception:
                logger.exception("Relance de paiement non envoyée à %s", relance.email)
    if envoyees:
        logger.info("Relances de paiement : %s e-mail(s) envoyé(s)", envoyees)
    return envoyees


def _en_tache_de_fond():
    close_old_connections()
    try:
        envoyer_relances()
    except Exception:
        logger.exception("Relances de paiement impossibles")
    finally:
        close_old_connections()


def verifier_relances():
    """Appelé au fil des visites : au plus un passage par heure, en tâche de fond."""
    if not getattr(settings, 'RELANCES_AU_FIL_DES_VISITES', True):
        return
    if not cache.add(CLE_VERIFICATION, 1, INTERVALLE_VERIFICATION):
        return
    if getattr(settings, 'PUSH_ASYNC', True):
        threading.Thread(target=_en_tache_de_fond, daemon=True).start()
    else:
        _en_tache_de_fond()
