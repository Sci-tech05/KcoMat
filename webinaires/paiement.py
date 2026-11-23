"""Attestation payante : participation gratuite, attestation téléchargeable après paiement (FedaPay).

Le paiement n'est proposé qu'aux participants présents, une fois la séance terminée. Il est vérifié
auprès de FedaPay (montant, devise, participation concernée) au retour du navigateur ou par le webhook ;
l'attestation est alors envoyée par e-mail et reste téléchargeable depuis la page du webinaire.
"""
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from api.fedapay_service import create_fedapay_transaction, verify_fedapay_payment
from core import tranches
from core.notifications_admin import notifier_admin
from core.pdf_invoices import build_invoice_response

from .attestation import generer_pdf, nom_fichier
from .models import ParticipationWebinaire

logger = logging.getLogger(__name__)

TYPE_PAIEMENT = 'webinaire_attestation'


def paiement_requis(participation):
    """Présent à une séance terminée dont l'attestation est payante et pas encore réglée."""
    return (participation.a_participe and not participation.attestation_reglee
            and participation.webinaire.statut() == 'termine')


def _verifier(participation, candidate_id=None):
    valide = verify_fedapay_payment(
        stored_transaction_id=participation.fedapay_attestation_id,
        candidate_transaction_id=candidate_id,
        expected_amount=participation.montant_attestation_du,
        expected_type=TYPE_PAIEMENT,
        ref_key='participation_id',
        expected_ref=participation.pk,
    )
    if valide and valide != participation.fedapay_attestation_id:
        participation.fedapay_attestation_id = valide
        participation.save(update_fields=['fedapay_attestation_id'])
    return bool(valide)


def confirmer(participation, candidate_id=None):
    """Enregistre le paiement en attente ; True si l'attestation est (désormais) réglée."""
    if participation.attestation_reglee:
        return True
    if not participation.fedapay_attestation_id and not candidate_id:
        return False
    if not _verifier(participation, candidate_id):
        return False
    if ParticipationWebinaire.objects.filter(pk=participation.pk, attestation_payee_le__isnull=True).update(
            attestation_payee_le=timezone.now()):
        participation.refresh_from_db()
        _apres_paiement(participation)
    return True


def facture(participation):
    return build_invoice_response(
        filename=f'facture-attestation-webinaire-{participation.pk}.pdf',
        title='Facture attestation',
        invoice_number=f'WEB-ATT-{participation.pk:06d}',
        customer_name=participation.nom_complet,
        customer_email=participation.email,
        customer_phone='',
        customer_address='',
        status_label='Payee' if participation.attestation_payee_le else 'En attente de paiement',
        items=[{'description': f"Attestation de participation - {participation.webinaire.titre}", 'quantity': 1,
                'unit_price': participation.montant_attestation_du, 'subtotal': participation.montant_attestation_du}],
        total_amount=participation.montant_attestation_du,
        note='Participation gratuite ; attestation nominative verifiable par QR code.',
    )


def _apres_paiement(participation):
    webinaire = participation.webinaire
    try:
        notifier_admin(
            type_evenement='paiement',
            sujet=f"Attestation payée : {webinaire.titre} — {participation.nom_complet}",
            titre="Attestation de webinaire payée",
            intro=f"{participation.nom_complet} a payé son attestation ({tranches.fcfa(participation.montant_attestation_du)}).",
            details=[('Webinaire', webinaire.titre), ('Participant', participation.nom_complet),
                     ('E-mail', participation.email), ('Montant', tranches.fcfa(participation.montant_attestation_du)),
                     ('Transaction FedaPay', participation.fedapay_attestation_id)],
            objet=participation, repondre_a=participation.email,
        )
    except Exception:
        logger.exception("Notification du paiement d'attestation #%s impossible", participation.pk)
    try:
        message = EmailMessage(
            subject=f"KcoMat — Votre attestation : {webinaire.titre}",
            body=(f"Bonjour {participation.prenom},\n\n"
                  f"Merci pour votre règlement. Votre attestation de participation au webinaire « {webinaire.titre} » "
                  "est jointe à ce message, avec votre facture. Elle reste téléchargeable depuis la page du webinaire.\n\n"
                  f"À bientôt pour un prochain webinaire,\nL'équipe KcoMat\n{settings.KCOMAT_INFO['phone']}"),
            to=[participation.email], reply_to=[settings.KCOMAT_INFO['email']],
        )
        message.attach(nom_fichier(participation), generer_pdf(participation), 'application/pdf')
        message.attach(f'facture-attestation-{participation.pk}.pdf', facture(participation).content, 'application/pdf')
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Attestation payée #%s non envoyée par e-mail", participation.pk)


@login_required
def paiement_attestation(request, slug):
    participation = get_object_or_404(ParticipationWebinaire.objects.select_related('webinaire'),
                                      webinaire__slug=slug, utilisateur=request.user)
    page = reverse('webinaires:detail', args=[slug])
    if not participation.webinaire.attestation_payante:
        return redirect(page)
    if confirmer(participation, request.GET.get('id')):          # déjà payée, ou retour de FedaPay
        messages.success(request, "Votre attestation est réglée : téléchargez-la ci-dessous (elle vous a aussi été envoyée par e-mail).")
        return redirect(page)
    if not paiement_requis(participation):
        messages.info(request, "L'attestation est réservée aux personnes présentes, une fois la séance terminée.")
        return redirect(page)

    participation.montant_attestation = participation.montant_attestation_du
    app_url = settings.FEDAPAY_APP_URL or request.build_absolute_uri('/').rstrip('/')
    retour = app_url + reverse('webinaires:paiement_attestation', args=[slug])
    try:
        data = create_fedapay_transaction({
            'amount': participation.montant_attestation,
            'description': f"Attestation webinaire KcoMat - {participation.webinaire.titre}"[:255],
            'currency': settings.PAYMENT_CONFIG['currency'],
            'country': settings.PAYMENT_CONFIG['country'],
            'customer': {'firstname': participation.prenom, 'lastname': participation.nom, 'email': participation.email},
            'callback_url': app_url + reverse('webinaires:callback_attestation', args=[participation.pk]),
            'metadata': {'source': 'KcoMat', 'type': TYPE_PAIEMENT, 'participation_id': str(participation.pk),
                         'success_url': retour, 'cancel_url': app_url + page},
        })
    except Exception:
        logger.exception("Transaction d'attestation #%s impossible", participation.pk)
        data = {}
    if not data.get('success') or not data.get('transaction_id'):
        messages.error(request, "Le paiement en ligne n'a pas pu démarrer (" + str(data.get('error', 'erreur inconnue'))
                       + "). Réessayez dans un instant.")
        return redirect(page)
    participation.fedapay_attestation_id = str(data['transaction_id'])
    participation.save(update_fields=['montant_attestation', 'fedapay_attestation_id'])
    return render(request, 'webinaires/paiement_attestation.html', {
        'participation': participation,
        'webinaire': participation.webinaire,
        'token': data.get('token', ''),
        'checkout_url': data.get('checkout_url', ''),
        'sandbox': settings.FEDAPAY_SANDBOX,
        'title': "Paiement de l'attestation",
    })


@csrf_exempt
def callback_attestation(request, pk):
    """Retour navigateur (GET) ou webhook FedaPay (POST) : paiement revérifié auprès de FedaPay."""
    participation = get_object_or_404(ParticipationWebinaire.objects.select_related('webinaire'), pk=pk)
    if request.method == 'GET':
        confirmer(participation, request.GET.get('id'))
        return redirect('webinaires:detail', slug=participation.webinaire.slug)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if data.get('name') == 'transaction.approved':
                confirmer(participation, data.get('data', {}).get('transaction', {}).get('id'))
        except Exception:
            logger.exception("Webhook d'attestation #%s illisible", participation.pk)
    return HttpResponse(status=200)
