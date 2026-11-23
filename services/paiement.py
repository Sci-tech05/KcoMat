"""Paiement en ligne (FedaPay) des frais de consultation de l'accompagnement de projet.

Même circuit que les frais d'inscription aux formations : transaction créée par le serveur,
paiement sur FedaPay, puis vérification (montant, devise, demande concernée) au retour,
par le webhook ou à l'affichage de la confirmation.
"""
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from api.fedapay_service import create_fedapay_transaction, verify_fedapay_payment
from core.acces import acces_autorise
from core.notifications_admin import notifier_admin
from core.pdf_invoices import build_invoice_response

from .models import ACCOMPAGNEMENT_SLUG, FRAIS_CONSULTATION, DemandeService

logger = logging.getLogger(__name__)

SESSION_DEMANDES_KEY = 'kcomat_demandes_accompagnement'
TYPE_TRANSACTION = 'consultation_accompagnement'


def memoriser_demande(request, demande):
    """Le visiteur qui a envoyé la demande (sans compte) peut payer et voir sa facture depuis sa session."""
    ids = set(request.session.get(SESSION_DEMANDES_KEY, []))
    ids.add(demande.pk)
    request.session[SESSION_DEMANDES_KEY] = sorted(ids)


def _demande(request, pk):
    demande = get_object_or_404(DemandeService.objects.select_related('service'), pk=pk,
                                service__slug=ACCOMPAGNEMENT_SLUG)
    if not (request.user.is_staff or pk in request.session.get(SESSION_DEMANDES_KEY, [])
            or acces_autorise(request, demande)):   # lien signé d'un e-mail de relance
        raise PermissionDenied("Accès refusé à cette demande.")
    return demande


def _verifier_paiement(demande, candidate_id=None):
    valide = verify_fedapay_payment(
        stored_transaction_id=demande.fedapay_consultation_id,
        candidate_transaction_id=candidate_id,
        expected_amount=FRAIS_CONSULTATION,
        expected_type=TYPE_TRANSACTION,
        ref_key='demande_id',
        expected_ref=demande.pk,
    )
    if valide and valide != demande.fedapay_consultation_id:
        demande.fedapay_consultation_id = valide
        demande.save(update_fields=['fedapay_consultation_id'])
    return bool(valide)


def _facture(demande):
    return build_invoice_response(
        filename=f'facture-consultation-{demande.pk}.pdf',
        title='Facture consultation',
        invoice_number=demande.numero_facture,
        customer_name=demande.nom,
        customer_email=demande.email,
        customer_phone=demande.telephone,
        customer_address=demande.localite,
        status_label='Payee' if demande.consultation_payee else 'En attente de paiement',
        items=[{
            'description': f"Session de consultation - {demande.intitule_projet or 'Accompagnement de projet'}",
            'quantity': 1,
            'unit_price': FRAIS_CONSULTATION,
            'subtotal': FRAIS_CONSULTATION,
        }],
        total_amount=FRAIS_CONSULTATION,
        note="Etape 1 de l'accompagnement de projet KcoMat : session de consultation.",
    )


def _marquer_payee(demande):
    """Une seule fois : date de paiement, e-mail à l'équipe, facture au demandeur."""
    if demande.consultation_payee:
        return
    if not DemandeService.objects.filter(pk=demande.pk, consultation_payee_le__isnull=True).update(
            consultation_payee_le=timezone.now()):
        return      # déjà traitée par un autre appel (webhook et retour navigateur simultanés)
    demande.refresh_from_db()
    try:
        notifier_admin(
            type_evenement='paiement', sujet=f"Consultation payée : {demande.intitule_projet} — {demande.nom}",
            titre='Frais de consultation reçus',
            intro=f"{demande.nom} a réglé la session de consultation ({FRAIS_CONSULTATION} FCFA) : "
                  "prenez contact pour fixer la séance.",
            details=[('Intitulé du projet', demande.intitule_projet), ('Nom', demande.nom), ('E-mail', demande.email),
                     ('Téléphone', demande.telephone), ('Adresse / Ville', demande.localite),
                     ('Établissement / structure', demande.structure), ('Transaction FedaPay', demande.fedapay_consultation_id),
                     ('Demande', f"#{demande.pk}")],
            message=demande.description_besoin, objet=demande, repondre_a=demande.email,
        )
    except Exception:
        logger.exception("Notification admin du paiement de consultation #%s impossible", demande.pk)
    try:
        message = EmailMessage(
            subject=f"KcoMat — Consultation réglée : {demande.intitule_projet}",
            body=(f"Bonjour {demande.nom},\n\n"
                  f"Nous avons bien reçu le règlement de votre session de consultation ({FRAIS_CONSULTATION} FCFA) "
                  f"pour le projet « {demande.intitule_projet} ».\n\n"
                  "Notre équipe vous contacte très vite pour fixer la date de la séance. Votre facture est jointe.\n\n"
                  f"Merci pour votre confiance,\nL'équipe KcoMat\n{settings.KCOMAT_INFO['phone']}"),
            to=[demande.email], reply_to=[settings.KCOMAT_INFO['email']],
        )
        message.attach(f'facture-consultation-{demande.pk}.pdf', _facture(demande).content, 'application/pdf')
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Facture de consultation #%s non envoyée", demande.pk)


def paiement_consultation(request, pk):
    demande = _demande(request, pk)
    if demande.consultation_payee:
        return redirect('services:confirmation_consultation', pk=demande.pk)

    app_url = settings.FEDAPAY_APP_URL or request.build_absolute_uri('/').rstrip('/')
    page_service = reverse('services:detail', args=[ACCOMPAGNEMENT_SLUG])
    nom, _, prenoms = demande.nom.strip().partition(' ')
    payload = {
        'amount': FRAIS_CONSULTATION,
        'description': f"Consultation KcoMat — {demande.intitule_projet}"[:255],
        'currency': settings.PAYMENT_CONFIG['currency'],
        'country': settings.PAYMENT_CONFIG['country'],
        # « Nom et prénom(s) » saisi en un seul champ : premier mot = nom, le reste = prénom(s)
        'customer': {'lastname': nom, 'firstname': prenoms or nom, 'email': demande.email, 'phone': demande.telephone},
        'callback_url': app_url + reverse('services:callback_consultation', args=[demande.pk]),
        'metadata': {
            'source': 'KcoMat',
            'type': TYPE_TRANSACTION,
            'demande_id': str(demande.pk),
            'projet': demande.intitule_projet,
            'success_url': app_url + reverse('services:confirmation_consultation', args=[demande.pk]),
            'cancel_url': app_url + page_service,
        },
    }
    try:
        data = create_fedapay_transaction(payload)
    except Exception:
        logger.exception("Création de la transaction de consultation #%s impossible", demande.pk)
        data = {'error': "erreur inattendue"}
    if not data.get('success') or not data.get('transaction_id'):
        logger.warning("FedaPay : transaction de consultation #%s refusée : %s", demande.pk, data)
        messages.error(request, "Le paiement en ligne n'a pas pu démarrer (" + str(data.get('error', 'erreur inconnue'))
                       + "). Réessayez dans un instant ou contactez-nous sur WhatsApp.")
        return redirect(page_service)

    demande.fedapay_consultation_id = str(data['transaction_id'])
    demande.save(update_fields=['fedapay_consultation_id'])
    return render(request, 'services/paiement_consultation.html', {
        'demande': demande,
        'frais': FRAIS_CONSULTATION,
        'title': "Paiement de la consultation",
        'token': data.get('token', ''),
        'checkout_url': data.get('checkout_url', ''),
        'sandbox': settings.FEDAPAY_SANDBOX,
    })


@csrf_exempt
def callback_consultation(request, pk):
    """Retour navigateur (GET) ou webhook FedaPay (POST) : le paiement est revérifié auprès de FedaPay."""
    demande = get_object_or_404(DemandeService, pk=pk, service__slug=ACCOMPAGNEMENT_SLUG)
    if request.method == 'GET':
        if not demande.consultation_payee and _verifier_paiement(demande, request.GET.get('id')):
            _marquer_payee(demande)
        return redirect('services:confirmation_consultation', pk=demande.pk)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            transaction = data.get('data', {}).get('transaction', {})
            if (data.get('name') == 'transaction.approved' and not demande.consultation_payee
                    and _verifier_paiement(demande, transaction.get('id'))):
                _marquer_payee(demande)
        except Exception:
            logger.exception("Webhook de consultation #%s illisible", demande.pk)
    return HttpResponse(status=200)


def confirmation_consultation(request, pk):
    demande = _demande(request, pk)
    if not demande.consultation_payee and demande.fedapay_consultation_id:
        if _verifier_paiement(demande, request.GET.get('id')):
            _marquer_payee(demande)
            demande.refresh_from_db()
        else:
            messages.warning(request, "Paiement en attente de confirmation par FedaPay. Rechargez cette page dans "
                                      "quelques secondes.")
    return render(request, 'services/confirmation_consultation.html', {
        'demande': demande,
        'frais': FRAIS_CONSULTATION,
        'title': "Demande d'accompagnement",
    })


def facture_consultation(request, pk):
    return _facture(_demande(request, pk))
