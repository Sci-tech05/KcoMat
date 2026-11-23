"""Paiement en ligne (FedaPay) des frais de stage des offres payantes, en 1 ou 2 tranches.

Ouvert une fois la candidature retenue, via un lien personnel (/carrieres/paiement/<code>/) envoyé
au candidat : pas de compte nécessaire. Chaque tranche est vérifiée auprès de FedaPay (montant,
devise, type et candidature concernée), au retour du navigateur ou par le webhook.
"""
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from api.fedapay_service import create_fedapay_transaction, verify_fedapay_payment
from core import tranches
from core.notifications_admin import notifier_admin
from core.pdf_invoices import build_invoice_response

from .models import Candidature

logger = logging.getLogger(__name__)

TYPE_PREMIER = 'stage_frais'
TYPE_SOLDE = 'stage_solde'


def url_paiement(candidature):
    base = (getattr(settings, 'FEDAPAY_APP_URL', '') or '').rstrip('/')
    return base + reverse('carrieres:paiement_frais', args=[candidature.code_paiement])


def _candidature(code):
    candidature = get_object_or_404(Candidature.objects.select_related('offre', 'formule'), code_paiement=code)
    if not candidature.paiement_ouvert:
        raise Http404("Aucun paiement attendu pour cette candidature.")
    return candidature


# --------------------------------------------------------------------------- vérification
def _verifier(candidature, solde, candidate_id=None):
    champ = 'fedapay_solde_id' if solde else 'fedapay_tranche1_id'
    valide = verify_fedapay_payment(
        stored_transaction_id=getattr(candidature, champ),
        candidate_transaction_id=candidate_id,
        expected_amount=candidature.montant_solde if solde else candidature.montant_premier_paiement,
        expected_type=TYPE_SOLDE if solde else TYPE_PREMIER,
        ref_key='candidature_id',
        expected_ref=candidature.pk,
    )
    if valide and valide != getattr(candidature, champ):
        setattr(candidature, champ, valide)
        candidature.save(update_fields=[champ])
    return bool(valide)


def _confirmer(candidature, candidate_id=None):
    """Enregistre le paiement en attente (1re tranche / total, puis solde). True si un paiement est validé."""
    if candidature.tranche1_payee_le is None:
        if candidature.fedapay_tranche1_id and _verifier(candidature, False, candidate_id):
            if Candidature.objects.filter(pk=candidature.pk, tranche1_payee_le__isnull=True).update(
                    tranche1_payee_le=timezone.now()):
                candidature.refresh_from_db()
                _apres_paiement(candidature, premier=True)
            return True
    elif candidature.reste_a_payer and candidature.fedapay_solde_id and _verifier(candidature, True, candidate_id):
        if Candidature.objects.filter(pk=candidature.pk, solde_paye_le__isnull=True).update(solde_paye_le=timezone.now()):
            candidature.refresh_from_db()
            _apres_paiement(candidature, premier=False)
        return True
    return False


# --------------------------------------------------------------------------- facture et e-mails
def facture(candidature):
    libelle = f"Frais de stage - {candidature.offre.titre}"
    if candidature.formule_id:
        libelle += f" ({candidature.formule.duree})"
    if candidature.en_deux_tranches:
        note = (f"Paiement en 2 tranches - 1re tranche : {tranches.fcfa(candidature.montant_premier_paiement)}, "
                f"solde : {tranches.fcfa(candidature.montant_solde)}. "
                + (f"Reste a payer : {tranches.fcfa(candidature.reste_a_payer)}." if candidature.reste_a_payer
                   else "Frais entierement regles."))
    else:
        note = 'Frais de stage KcoMat.'
    if not candidature.tranche1_payee_le:
        statut = 'En attente de paiement'
    elif candidature.reste_a_payer:
        statut = '1re tranche payee (50 %)'
    else:
        statut = 'Payee'
    return build_invoice_response(
        filename=f'facture-frais-stage-{candidature.pk}.pdf',
        title='Facture frais de stage',
        invoice_number=f'STG-{candidature.pk:06d}',
        customer_name=candidature.nom_complet,
        customer_email=candidature.email,
        customer_phone=candidature.telephone,
        customer_address='',
        status_label=statut,
        items=[{'description': libelle, 'quantity': 1, 'unit_price': candidature.frais_a_payer,
                'subtotal': candidature.frais_a_payer}],
        total_amount=candidature.frais_a_payer,
        note=note,
    )


def _apres_paiement(candidature, premier):
    montant = candidature.montant_premier_paiement if premier else candidature.montant_solde
    reste = candidature.reste_a_payer
    try:
        notifier_admin(
            type_evenement='paiement',
            sujet=f"Frais de stage reçus : {candidature.nom_complet} — {candidature.offre.titre}",
            titre='Frais de stage reçus',
            intro=(f"{candidature.nom_complet} a payé {tranches.fcfa(montant)} de frais de stage"
                   + (f" (1re tranche) ; reste {tranches.fcfa(reste)}." if reste else " : frais entièrement réglés.")),
            details=[('Offre', candidature.offre.titre), ('Formule', str(candidature.formule or '—')),
                     ('Candidat', candidature.nom_complet), ('E-mail', candidature.email),
                     ('Téléphone', candidature.telephone), ('Montant total', tranches.fcfa(candidature.frais_a_payer)),
                     ('Déjà payé', tranches.fcfa(candidature.montant_paye)), ('Reste à payer', tranches.fcfa(reste))],
            objet=candidature, repondre_a=candidature.email,
        )
    except Exception:
        logger.exception("Notification du paiement de la candidature #%s impossible", candidature.pk)
    try:
        corps = (f"Bonjour {candidature.prenom},\n\n"
                 f"Nous avons bien reçu {tranches.fcfa(montant)} au titre des frais de stage pour « {candidature.offre.titre} ».\n"
                 + (f"Il reste {tranches.fcfa(reste)} à régler avant le début du stage, avec le même lien :\n"
                    f"{url_paiement(candidature)}\n" if reste else "Vos frais de stage sont entièrement réglés.\n")
                 + f"\nVotre facture est jointe.\n\nÀ très vite,\nL'équipe KcoMat\n{settings.KCOMAT_INFO['phone']}")
        message = EmailMessage(subject=f"KcoMat — Frais de stage reçus : {candidature.offre.titre}", body=corps,
                               to=[candidature.email], reply_to=[settings.KCOMAT_INFO['email']])
        message.attach(f'facture-frais-stage-{candidature.pk}.pdf', facture(candidature).content, 'application/pdf')
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Reçu des frais de stage #%s non envoyé", candidature.pk)


# --------------------------------------------------------------------------- vues
def paiement_frais(request, code):
    """Page du lien personnel : choix total / 2 tranches, puis paiement ; ensuite paiement du solde."""
    candidature = _candidature(code)
    _confirmer(candidature, request.GET.get('id'))       # retour de FedaPay
    candidature.refresh_from_db()

    if not candidature.reste_a_payer:
        return render(request, 'carrieres/paiement_frais.html', {'candidature': candidature, 'etape': 'regle',
                                                                 'title': 'Frais de stage'})
    premier = candidature.tranche1_payee_le is None
    option = request.GET.get('option')
    if premier and option not in (tranches.TOTAL, 'moitie'):
        frais = candidature.frais_a_payer
        return render(request, 'carrieres/paiement_frais.html', {
            'candidature': candidature, 'etape': 'choix', 'frais': frais,
            'premiere_tranche': tranches.premiere_tranche(frais), 'solde': tranches.solde(frais),
            'title': 'Frais de stage',
        })
    if not premier and option != 'solde':
        # 1re tranche reçue : état du paiement et bouton « Payer le solde »
        return render(request, 'carrieres/paiement_frais.html', {'candidature': candidature, 'etape': 'solde',
                                                                 'title': 'Frais de stage'})

    if premier:
        candidature.mode_paiement = tranches.DEUX_TRANCHES if option == 'moitie' else tranches.TOTAL
        candidature.montant_frais = candidature.frais_a_payer
        candidature.save(update_fields=['mode_paiement', 'montant_frais'])
        montant, type_paiement, champ = candidature.montant_premier_paiement, TYPE_PREMIER, 'fedapay_tranche1_id'
        libelle = 'Frais de stage - 1re tranche (50 %)' if candidature.en_deux_tranches else 'Frais de stage'
    else:
        montant, type_paiement, champ = candidature.montant_solde, TYPE_SOLDE, 'fedapay_solde_id'
        libelle = 'Frais de stage - solde (2e tranche)'

    app_url = settings.FEDAPAY_APP_URL or request.build_absolute_uri('/').rstrip('/')
    page = app_url + reverse('carrieres:paiement_frais', args=[candidature.code_paiement])
    try:
        data = create_fedapay_transaction({
            'amount': montant,
            'description': f"{libelle} - {candidature.offre.titre}"[:255],
            'currency': settings.PAYMENT_CONFIG['currency'],
            'country': settings.PAYMENT_CONFIG['country'],
            'customer': {'firstname': candidature.prenom, 'lastname': candidature.nom,
                         'email': candidature.email, 'phone': candidature.telephone},
            'callback_url': app_url + reverse('carrieres:callback_frais', args=[candidature.code_paiement]),
            'metadata': {'source': 'KcoMat', 'type': type_paiement, 'candidature_id': str(candidature.pk),
                         'success_url': page, 'cancel_url': page},
        })
    except Exception:
        logger.exception("Transaction des frais de stage #%s impossible", candidature.pk)
        data = {}
    if not data.get('success') or not data.get('transaction_id'):
        messages.error(request, "Le paiement en ligne n'a pas pu démarrer (" + str(data.get('error', 'erreur inconnue'))
                       + "). Réessayez dans un instant ou contactez-nous sur WhatsApp.")
        return redirect('carrieres:paiement_frais', code=candidature.code_paiement)
    setattr(candidature, champ, str(data['transaction_id']))
    candidature.save(update_fields=[champ])
    return render(request, 'carrieres/paiement_frais.html', {
        'candidature': candidature, 'etape': 'redirection', 'montant': montant, 'libelle': libelle,
        'token': data.get('token', ''), 'checkout_url': data.get('checkout_url', ''),
        'sandbox': settings.FEDAPAY_SANDBOX, 'title': 'Paiement des frais de stage',
    })


@csrf_exempt
def callback_frais(request, code):
    candidature = get_object_or_404(Candidature, code_paiement=code)
    if request.method == 'GET':
        if candidature.paiement_ouvert:
            _confirmer(candidature, request.GET.get('id'))
        return redirect('carrieres:paiement_frais', code=code)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            transaction = data.get('data', {}).get('transaction', {})
            if data.get('name') == 'transaction.approved' and candidature.paiement_ouvert:
                _confirmer(candidature, transaction.get('id'))
        except Exception:
            logger.exception("Webhook des frais de stage #%s illisible", candidature.pk)
    return HttpResponse(status=200)


def facture_frais(request, code):
    candidature = _candidature(code)
    if not candidature.tranche1_payee_le:
        raise Http404("Aucun paiement enregistré.")
    return facture(candidature)
