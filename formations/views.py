import json
import logging
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.core.mail import EmailMessage
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Formation, Inscription, CategorieFormation
from .forms import InscriptionForm
from core.pdf_invoices import build_invoice_response


logger = logging.getLogger(__name__)


def _build_frais_invoice_response(inscription):
    frais = settings.KCOMAT_INFO['frais_inscription']
    items = [{
        'description': f"Frais d'inscription - {inscription.formation.titre}",
        'quantity': 1,
        'unit_price': frais,
        'subtotal': frais,
    }]

    status_label = 'Payee' if inscription.frais_payes_le else 'En attente de paiement'

    return build_invoice_response(
        filename=f'facture-frais-inscription-{inscription.pk}.pdf',
        title='Facture frais inscription',
        invoice_number=f'INS-FRAIS-{inscription.pk:06d}',
        customer_name=f'{inscription.prenom} {inscription.nom}',
        customer_email=inscription.email,
        customer_phone=inscription.telephone,
        customer_address=inscription.adresse,
        status_label=status_label,
        items=items,
        total_amount=frais,
        note='Paiement des frais administratifs d inscription KcoMat.',
    )


def _build_formation_invoice_response(inscription):
    montant = inscription.formation.prix
    items = [{
        'description': f"Formation - {inscription.formation.titre}",
        'quantity': 1,
        'unit_price': montant,
        'subtotal': montant,
    }]

    is_paid = inscription.formation_payee_le is not None or inscription.statut == 'complet'
    status_label = 'Payee' if is_paid else 'Non payee'

    return build_invoice_response(
        filename=f'facture-formation-{inscription.pk}.pdf',
        title='Facture formation',
        invoice_number=f'INS-FORM-{inscription.pk:06d}',
        customer_name=f'{inscription.prenom} {inscription.nom}',
        customer_email=inscription.email,
        customer_phone=inscription.telephone,
        customer_address=inscription.adresse,
        status_label=status_label,
        items=items,
        total_amount=montant,
        note='Formation professionnelle KcoMat.',
    )


def _send_inscription_invoice_email(inscription):
    recipient = (inscription.email or '').strip()
    if not recipient:
        return

    has_frais_paid = inscription.frais_payes_le is not None or inscription.statut in ['frais_payes', 'complet']
    has_formation_paid = inscription.formation_payee_le is not None or inscription.statut == 'complet'

    if not has_frais_paid and not has_formation_paid:
        return

    subject = f'KcoMat - Vos factures inscription #{inscription.pk}'
    body = (
        f"Bonjour {inscription.prenom} {inscription.nom},\n\n"
        f"Votre paiement a ete confirme pour la formation: {inscription.formation.titre}.\n"
        f"Veuillez trouver votre ou vos factures en piece jointe.\n\n"
        "Merci pour votre confiance.\n"
        "KcoMat"
    )

    message = EmailMessage(subject=subject, body=body, to=[recipient])

    if has_frais_paid:
        frais_response = _build_frais_invoice_response(inscription)
        message.attach(
            f'facture-frais-inscription-{inscription.pk}.pdf',
            frais_response.content,
            'application/pdf',
        )

    if has_formation_paid:
        formation_response = _build_formation_invoice_response(inscription)
        message.attach(
            f'facture-formation-{inscription.pk}.pdf',
            formation_response.content,
            'application/pdf',
        )

    message.send(fail_silently=False)


def liste_formations(request):
    categories = CategorieFormation.objects.all()
    cat_slug = request.GET.get('categorie', '')
    formations = Formation.objects.filter(actif=True)
    if cat_slug:
        formations = formations.filter(categorie__slug=cat_slug)
    ctx = {
        'formations': formations,
        'categories': categories,
        'cat_active': cat_slug,
        'title': 'Nos Formations',
    }
    return render(request, 'formations/liste.html', ctx)


def detail_formation(request, slug):
    formation = get_object_or_404(Formation, slug=slug, actif=True)
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
    elif request.user.is_authenticated:
        profil = getattr(request.user, 'profil_kcomat', None)
        form = InscriptionForm(initial={
            'prenom': request.user.first_name,
            'nom': request.user.last_name,
            'email': request.user.email,
            'telephone': getattr(profil, 'telephone', ''),
            'adresse': getattr(profil, 'adresse', ''),
        })
    else:
        form = InscriptionForm()

    if request.method == 'POST' and form.is_valid():
        inscription = form.save(commit=False)
        inscription.formation = formation
        if request.user.is_authenticated:
            inscription.utilisateur = request.user
        inscription.save()
        # Rediriger vers le paiement des frais d'inscription
        return redirect('formations:paiement_frais', pk=inscription.pk)
    ctx = {
        'formation': formation,
        'form': form,
        'frais': settings.KCOMAT_INFO['frais_inscription'],
        'title': formation.titre,
    }
    return render(request, 'formations/detail.html', ctx)


def paiement_frais(request, pk):
    """Initie le paiement des frais d'inscription (2000 FCFA) via Fedapay Checkout.js."""
    inscription = get_object_or_404(Inscription, pk=pk)
    if inscription.statut != 'en_attente':
        messages.warning(request, "Cette inscription a déjà été traitée.")
        return redirect('formations:liste')

    app_url = settings.FEDAPAY_APP_URL or request.build_absolute_uri('/').rstrip('/')
    callback_url = f"{app_url}/formations/inscription/{inscription.pk}/callback-frais/"
    success_url = settings.FEDAPAY_SUCCESS_URL or f"{app_url}/formations/inscription/{inscription.pk}/succes/"
    cancel_url = settings.FEDAPAY_CANCEL_URL or f"{app_url}/formations/{inscription.formation.slug}/"
    
    # Appeler l'endpoint API local pour créer la transaction FedaPay
    api_url = request.build_absolute_uri('/') + 'api/create-transaction/'
    
    transaction_payload = {
        'amount': settings.KCOMAT_INFO['frais_inscription'],
        'description': f"Frais d'inscription KcoMat — {inscription.formation.titre}",
        'currency': settings.PAYMENT_CONFIG['currency'],
        'country': settings.PAYMENT_CONFIG['country'],
        'customer': {
            'firstname': inscription.prenom,
            'lastname': inscription.nom,
            'email': inscription.email,
            'phone': inscription.telephone,
        },
        'callback_url': callback_url,
        'metadata': {
            'source': 'KcoMat',
            'type': 'inscription_frais',
            'inscription_id': str(inscription.pk),
            'formation': inscription.formation.titre,
            'success_url': success_url,
            'cancel_url': cancel_url,
        }
    }

    try:
        resp = requests.post(api_url, json=transaction_payload, timeout=10)
        data = resp.json()
        
        if not data.get('success') or not data.get('transaction_id'):
            logger.warning(
                "KcoMat API create transaction failed (formations): status=%s response=%s",
                resp.status_code,
                data
            )
            messages.error(request, "Impossible de créer la transaction de paiement: " + data.get('error', 'Erreur inconnue'))
        else:
            # Sauvegarde l'ID de transaction FedaPay
            transaction_id = data['transaction_id']
            token = data['token']
            checkout_url = data.get('checkout_url', '')
            
            inscription.fedapay_frais_id = str(transaction_id)
            inscription.save(update_fields=['fedapay_frais_id'])
            
            logger.info("FedaPay transaction created (formations): %s", transaction_id)
            
            # Passer le token au template pour Checkout.js
            ctx = {
                'inscription': inscription,
                'frais': settings.KCOMAT_INFO['frais_inscription'],
                'title': "Paiement des frais d'inscription",
                'fedapay_public_key': settings.FEDAPAY_PUBLIC_KEY,
                'transaction_id': transaction_id,
                'token': token,
                'checkout_url': checkout_url,
                'sandbox': settings.FEDAPAY_SANDBOX,
            }
            return render(request, 'formations/paiement_checkout.html', ctx)
            
    except requests.RequestException as e:
        logger.exception("KcoMat API HTTP error (formations): %s", e)
        messages.error(request, "Erreur réseau lors de la connexion au service de paiement.")
    except Exception as e:
        logger.exception("Unexpected error creating transaction (formations): %s", e)
        messages.error(request, "Une erreur inattendue est survenue lors de l'initialisation du paiement.")

    # Fallback: rediriger vers la page de formation
    return redirect('formations:detail', slug=inscription.formation.slug)


def paiement_formation(request, pk):
    """Initie le paiement de la formation complete apres paiement des frais."""
    inscription = get_object_or_404(Inscription.objects.select_related('formation', 'utilisateur'), pk=pk)

    if inscription.utilisateur_id and (not request.user.is_authenticated or (request.user != inscription.utilisateur and not request.user.is_staff)):
        return HttpResponseForbidden('Acces refuse a ce paiement.')

    if inscription.statut == 'en_attente':
        messages.warning(request, "Veuillez d'abord payer les frais d'inscription.")
        return redirect('formations:paiement_frais', pk=inscription.pk)

    if inscription.statut == 'complet':
        messages.info(request, 'Cette formation est deja reglee.')
        return redirect('formations:mes_inscriptions')

    app_url = settings.FEDAPAY_APP_URL or request.build_absolute_uri('/').rstrip('/')
    callback_url = f"{app_url}/formations/inscription/{inscription.pk}/callback-formation/"
    success_url = settings.FEDAPAY_SUCCESS_URL or f"{app_url}/formations/inscription/{inscription.pk}/succes-formation/"
    cancel_url = settings.FEDAPAY_CANCEL_URL or f"{app_url}/formations/inscription/{inscription.pk}/succes/"

    api_url = request.build_absolute_uri('/') + 'api/create-transaction/'
    transaction_payload = {
        'amount': int(inscription.formation.prix),
        'description': f"Paiement formation KcoMat - {inscription.formation.titre}",
        'currency': settings.PAYMENT_CONFIG['currency'],
        'country': settings.PAYMENT_CONFIG['country'],
        'customer': {
            'firstname': inscription.prenom,
            'lastname': inscription.nom,
            'email': inscription.email,
            'phone': inscription.telephone,
        },
        'callback_url': callback_url,
        'metadata': {
            'source': 'KcoMat',
            'type': 'inscription_formation',
            'inscription_id': str(inscription.pk),
            'formation': inscription.formation.titre,
            'success_url': success_url,
            'cancel_url': cancel_url,
        }
    }

    try:
        resp = requests.post(api_url, json=transaction_payload, timeout=10)
        data = resp.json()

        if not data.get('success') or not data.get('transaction_id'):
            logger.warning(
                "KcoMat API create transaction failed (formation complete): status=%s response=%s",
                resp.status_code,
                data
            )
            messages.error(request, "Impossible de creer la transaction de paiement: " + data.get('error', 'Erreur inconnue'))
        else:
            transaction_id = data['transaction_id']
            token = data['token']
            checkout_url = data.get('checkout_url', '')

            inscription.fedapay_formation_id = str(transaction_id)
            inscription.save(update_fields=['fedapay_formation_id'])

            ctx = {
                'inscription': inscription,
                'montant_formation': inscription.formation.prix,
                'title': 'Paiement de la formation',
                'fedapay_public_key': settings.FEDAPAY_PUBLIC_KEY,
                'transaction_id': transaction_id,
                'token': token,
                'checkout_url': checkout_url,
                'sandbox': settings.FEDAPAY_SANDBOX,
            }
            return render(request, 'formations/paiement_formation_checkout.html', ctx)

    except requests.RequestException as e:
        logger.exception("KcoMat API HTTP error (formation complete): %s", e)
        messages.error(request, "Erreur reseau lors de la connexion au service de paiement.")
    except Exception as e:
        logger.exception("Unexpected error creating formation transaction: %s", e)
        messages.error(request, "Une erreur inattendue est survenue lors de l'initialisation du paiement.")

    return redirect('formations:mes_inscriptions')


@csrf_exempt
def callback_frais(request, pk):
    """Webhook Fedapay — confirmation paiement frais d'inscription."""
    inscription = get_object_or_404(Inscription, pk=pk)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = data.get('name', '')
            transaction = data.get('data', {}).get('transaction', {})
            if event == 'transaction.approved' and transaction.get('status') == 'approved' and inscription.statut == 'en_attente':
                inscription.statut = 'frais_payes'
                inscription.frais_payes_le = timezone.now()
                inscription.save(update_fields=['statut', 'frais_payes_le'])
                _send_inscription_invoice_email(inscription)
        except Exception as e:
            logger.exception("Erreur callback frais inscription #%s: %s", inscription.pk, e)
    return HttpResponse(status=200)


@csrf_exempt
def callback_formation(request, pk):
    """Webhook Fedapay — confirmation paiement formation complete."""
    inscription = get_object_or_404(Inscription, pk=pk)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = data.get('name', '')
            transaction = data.get('data', {}).get('transaction', {})
            if event == 'transaction.approved' and transaction.get('status') == 'approved' and inscription.statut in ['frais_payes', 'complet']:
                if inscription.statut == 'complet':
                    return HttpResponse(status=200)
                inscription.statut = 'complet'
                inscription.formation_payee_le = timezone.now()
                inscription.save(update_fields=['statut', 'formation_payee_le'])
                _send_inscription_invoice_email(inscription)
        except Exception as e:
            logger.exception("Erreur callback formation inscription #%s: %s", inscription.pk, e)
    return HttpResponse(status=200)


def succes_inscription(request, pk):
    inscription = get_object_or_404(Inscription, pk=pk)
    if inscription.statut == 'en_attente':
        # Marquer comme frais payés si on arrive ici depuis le checkout
        inscription.statut = 'frais_payes'
        inscription.frais_payes_le = timezone.now()
        inscription.save(update_fields=['statut', 'frais_payes_le'])
        try:
            _send_inscription_invoice_email(inscription)
        except Exception as e:
            logger.exception("Erreur envoi facture email inscription #%s: %s", inscription.pk, e)
            messages.warning(request, "Paiement confirme, mais l'envoi automatique de la facture a echoue. Vous pouvez la telecharger depuis votre espace.")
    ctx = {
        'inscription': inscription,
        'title': "Inscription confirmée !",
    }
    return render(request, 'formations/succes.html', ctx)


def succes_formation(request, pk):
    inscription = get_object_or_404(Inscription, pk=pk)
    if inscription.statut == 'en_attente':
        messages.warning(request, "Veuillez d'abord payer les frais d'inscription.")
        return redirect('formations:paiement_frais', pk=inscription.pk)

    if inscription.statut != 'complet':
        inscription.statut = 'complet'
        inscription.formation_payee_le = timezone.now()
        inscription.save(update_fields=['statut', 'formation_payee_le'])
        try:
            _send_inscription_invoice_email(inscription)
        except Exception as e:
            logger.exception("Erreur envoi facture formation email inscription #%s: %s", inscription.pk, e)
            messages.warning(request, "Paiement confirme, mais l'envoi automatique de la facture formation a echoue. Vous pouvez la telecharger depuis votre espace.")

    ctx = {
        'inscription': inscription,
        'title': 'Formation reglee avec succes',
    }
    return render(request, 'formations/succes.html', ctx)


def mes_inscriptions(request):
    if not request.user.is_authenticated:
        return redirect('accounts:connexion')
    inscriptions = Inscription.objects.filter(utilisateur=request.user).select_related('formation')
    return render(request, 'formations/mes_inscriptions.html', {
        'inscriptions': inscriptions,
        'title': 'Mes inscriptions',
    })


def facture_frais_pdf(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation', 'utilisateur'), pk=pk)

    if inscription.utilisateur_id and (not request.user.is_authenticated or (request.user != inscription.utilisateur and not request.user.is_staff)):
        return HttpResponseForbidden('Acces refuse a cette facture.')

    return _build_frais_invoice_response(inscription)


def facture_formation_pdf(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation', 'utilisateur'), pk=pk)

    if inscription.utilisateur_id and (not request.user.is_authenticated or (request.user != inscription.utilisateur and not request.user.is_staff)):
        return HttpResponseForbidden('Acces refuse a cette facture.')

    return _build_formation_invoice_response(inscription)
