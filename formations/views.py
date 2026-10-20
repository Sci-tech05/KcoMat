import json
import logging
import uuid
from urllib.parse import urlparse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Prefetch
from django.utils.text import slugify
from .models import Formation, FormationSessionPassee, Inscription, CategorieFormation
from .forms import InscriptionForm
from core.pdf_invoices import build_invoice_response
from api.fedapay_service import create_fedapay_transaction, verify_fedapay_payment


logger = logging.getLogger(__name__)


SESSION_INSCRIPTIONS_KEY = 'kcomat_inscriptions'


def _verify_frais_payment(inscription, candidate_id=None):
    """Valide le paiement des frais : transaction de CETTE inscription, bon montant."""
    validated_id = verify_fedapay_payment(
        stored_transaction_id=inscription.fedapay_frais_id,
        candidate_transaction_id=candidate_id,
        expected_amount=settings.KCOMAT_INFO['frais_inscription'],
        expected_type='inscription_frais',
        ref_key='inscription_id',
        expected_ref=inscription.pk,
    )
    if validated_id and validated_id != inscription.fedapay_frais_id:
        inscription.fedapay_frais_id = validated_id
        inscription.save(update_fields=['fedapay_frais_id'])
    return bool(validated_id)


def _verify_formation_payment(inscription, candidate_id=None):
    """Valide le paiement de la formation : transaction de CETTE inscription, prix de la formation."""
    validated_id = verify_fedapay_payment(
        stored_transaction_id=inscription.fedapay_formation_id,
        candidate_transaction_id=candidate_id,
        expected_amount=int(inscription.formation.prix),
        expected_type='inscription_formation',
        ref_key='inscription_id',
        expected_ref=inscription.pk,
    )
    if validated_id and validated_id != inscription.fedapay_formation_id:
        inscription.fedapay_formation_id = validated_id
        inscription.save(update_fields=['fedapay_formation_id'])
    return bool(validated_id)


def _remember_inscription(request, inscription):
    """Memorise en session les inscriptions creees par un visiteur (non connecte)."""
    ids = set(request.session.get(SESSION_INSCRIPTIONS_KEY, []))
    ids.add(inscription.pk)
    request.session[SESSION_INSCRIPTIONS_KEY] = sorted(ids)


def _peut_acceder(request, inscription):
    try:
        _check_inscription_access(request, inscription)
        return True
    except PermissionDenied:
        return False


def _etape_suivante(request, inscription):
    """URL de la prochaine étape d'une inscription : frais (2 000 F), puis formation, puis espace personnel."""
    if inscription.statut == 'en_attente':
        return reverse('formations:paiement_frais', args=[inscription.pk])
    if inscription.statut == 'frais_payes':
        return reverse('formations:paiement_formation', args=[inscription.pk])
    if request.user.is_authenticated:
        return reverse('formations:mes_inscriptions')
    return reverse('formations:succes_formation', args=[inscription.pk])


def _check_inscription_access(request, inscription):
    """Seul le proprietaire (compte ou session d'origine) ou le staff accede a l'inscription."""
    user = request.user
    if user.is_authenticated and (user.is_staff or inscription.utilisateur_id == user.pk):
        return
    if inscription.utilisateur_id is None and inscription.pk in request.session.get(SESSION_INSCRIPTIONS_KEY, []):
        return
    raise PermissionDenied("Acces refuse a cette inscription.")


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

    is_paid = inscription.formation_payee_le is not None or inscription.statut in Inscription.STATUTS_PAYES
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

    has_frais_paid = inscription.frais_payes_le is not None or inscription.statut in ('frais_payes', *Inscription.STATUTS_PAYES)
    has_formation_paid = inscription.formation_payee_le is not None or inscription.statut in Inscription.STATUTS_PAYES

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


def _mark_inscription_frais_paid(inscription):
    if inscription.statut != 'en_attente':
        return
    inscription.statut = 'frais_payes'
    inscription.frais_payes_le = timezone.now()
    inscription.save(update_fields=['statut', 'frais_payes_le'])
    _send_inscription_invoice_email(inscription)


def _mark_inscription_formation_paid(inscription):
    if inscription.statut in Inscription.STATUTS_PAYES:
        return
    if inscription.statut == 'en_attente':
        return
    inscription.statut = 'complet'
    inscription.formation_payee_le = timezone.now()
    inscription.save(update_fields=['statut', 'formation_payee_le'])
    _send_inscription_invoice_email(inscription)


def _ensure_jitsi_room(inscription):
    if inscription.jitsi_room_name:
        return inscription.jitsi_room_name
    base_slug = slugify(inscription.formation.titre)[:30] or 'formation'
    short_token = uuid.uuid4().hex[:8]
    room_name = f"kcomat-{inscription.pk}-{base_slug}-{short_token}"
    inscription.jitsi_room_name = room_name
    inscription.jitsi_room_created_at = timezone.now()
    inscription.save(update_fields=['jitsi_room_name', 'jitsi_room_created_at'])
    return room_name


def _can_access_meet_room(user, inscription):
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return inscription.utilisateur_id == user.pk and inscription.statut == 'complet'


def _jitsi_embed_payload(inscription, user):
    _ensure_jitsi_room(inscription)
    meet_url = inscription.get_jitsi_room_url()
    if not meet_url:
        return {
            'meet_url': '',
            'jitsi_domain': '',
            'jitsi_external_api_url': '',
            'jitsi_room_name': '',
            'jitsi_display_name': '',
            'jitsi_user_email': '',
        }
    parsed = urlparse(meet_url)
    scheme = parsed.scheme or 'https'
    domain = parsed.netloc
    room_name = parsed.path.lstrip('/')
    external_api_url = f"{scheme}://{domain}/external_api.js"
    display_name = (
        f"{user.first_name} {user.last_name}".strip()
        or getattr(user, 'username', '')
        or f"{inscription.prenom} {inscription.nom}".strip()
        or 'Participant KcoMat'
    )
    return {
        'meet_url': meet_url,
        'jitsi_domain': domain,
        'jitsi_external_api_url': external_api_url,
        'jitsi_room_name': room_name,
        'jitsi_display_name': display_name,
        'jitsi_user_email': getattr(user, 'email', '') or inscription.email or '',
    }


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
    formation = get_object_or_404(
        Formation.objects.prefetch_related(
            Prefetch(
                'sessions_passees',
                queryset=FormationSessionPassee.objects.filter(publiee=True),
            )
        ),
        slug=slug,
        actif=True,
    )
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

    # Une même personne ne peut avoir qu'une inscription en cours par formation
    # (une nouvelle inscription redevient possible une fois la formation terminée).
    inscription_existante = None
    if request.user.is_authenticated:
        inscription_existante = Inscription.inscription_en_cours(formation, utilisateur=request.user)
    if request.method == 'POST' and form.is_valid():
        existante = inscription_existante or Inscription.inscription_en_cours(
            formation, utilisateur=request.user, email=form.cleaned_data.get('email', ''))
        if existante:
            if _peut_acceder(request, existante):
                messages.info(request, "Vous êtes déjà inscrit(e) à cette formation : poursuivez votre inscription.")
                return redirect(_etape_suivante(request, existante))
            form.add_error('email', "Une inscription à cette formation est déjà en cours pour cette adresse e-mail. "
                                    "Connectez-vous à votre compte pour la poursuivre, ou contactez-nous.")
    if request.method == 'POST' and form.is_valid():
        inscription = form.save(commit=False)
        inscription.formation = formation
        if request.user.is_authenticated:
            inscription.utilisateur = request.user
        inscription.save()
        _remember_inscription(request, inscription)
        # Rediriger vers le paiement des frais d'inscription
        return redirect('formations:paiement_frais', pk=inscription.pk)
    ctx = {
        'formation': formation,
        'form': form,
        'frais': settings.KCOMAT_INFO['frais_inscription'],
        'inscription_existante': inscription_existante,
        'etape_suivante': _etape_suivante(request, inscription_existante) if inscription_existante else '',
        'title': formation.titre,
    }
    return render(request, 'formations/detail.html', ctx)


def paiement_frais(request, pk):
    """Initie le paiement des frais d'inscription (2000 FCFA) via Fedapay Checkout.js."""
    inscription = get_object_or_404(Inscription.objects.select_related('formation'), pk=pk)
    _check_inscription_access(request, inscription)
    if inscription.statut != 'en_attente':
        # Frais déjà réglés : on enchaîne directement sur l'étape suivante
        return redirect(_etape_suivante(request, inscription))

    app_url = settings.FEDAPAY_APP_URL or request.build_absolute_uri('/').rstrip('/')
    callback_url = f"{app_url}/formations/inscription/{inscription.pk}/callback-frais/"
    success_url = settings.FEDAPAY_SUCCESS_URL or f"{app_url}/formations/inscription/{inscription.pk}/succes/"
    cancel_url = settings.FEDAPAY_CANCEL_URL or f"{app_url}/formations/{inscription.formation.slug}/"

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
        data = create_fedapay_transaction(transaction_payload)
        if not data.get('success') or not data.get('transaction_id'):
            logger.warning("FedaPay create transaction failed (formations): response=%s", data)
            messages.error(request, "Impossible de créer la transaction de paiement: " + data.get('error', 'Erreur inconnue'))
        else:
            transaction_id = data['transaction_id']
            token = data['token']
            checkout_url = data.get('checkout_url', '')

            inscription.fedapay_frais_id = str(transaction_id)
            inscription.save(update_fields=['fedapay_frais_id'])

            logger.info("FedaPay transaction created (formations): %s", transaction_id)
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
    except Exception as e:
        logger.exception("Unexpected error creating transaction (formations): %s", e)
        messages.error(request, "Une erreur inattendue est survenue lors de l'initialisation du paiement.")

    return redirect('formations:detail', slug=inscription.formation.slug)


def paiement_formation(request, pk):
    """Initie le paiement de la formation complete apres paiement des frais."""
    inscription = get_object_or_404(Inscription.objects.select_related('formation', 'utilisateur'), pk=pk)
    _check_inscription_access(request, inscription)

    if inscription.statut == 'en_attente':
        messages.warning(request, "Veuillez d'abord payer les frais d'inscription.")
        return redirect('formations:paiement_frais', pk=inscription.pk)

    if inscription.statut in Inscription.STATUTS_PAYES:
        messages.info(request, 'Cette formation est deja reglee.')
        return redirect('formations:mes_inscriptions')

    app_url = settings.FEDAPAY_APP_URL or request.build_absolute_uri('/').rstrip('/')
    callback_url = f"{app_url}/formations/inscription/{inscription.pk}/callback-formation/"
    success_url = settings.FEDAPAY_SUCCESS_URL or f"{app_url}/formations/inscription/{inscription.pk}/succes-formation/"
    cancel_url = settings.FEDAPAY_CANCEL_URL or f"{app_url}/formations/inscription/{inscription.pk}/succes/"

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
        data = create_fedapay_transaction(transaction_payload)
        if not data.get('success') or not data.get('transaction_id'):
            logger.warning("FedaPay create transaction failed (formation complete): response=%s", data)
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
    except Exception as e:
        logger.exception("Unexpected error creating formation transaction: %s", e)
        messages.error(request, "Une erreur inattendue est survenue lors de l'initialisation du paiement.")

    return redirect('formations:mes_inscriptions')


@csrf_exempt
def callback_frais(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation'), pk=pk)
    if request.method == 'GET':
        if inscription.statut == 'en_attente' and _verify_frais_payment(inscription, request.GET.get('id')):
            try:
                _mark_inscription_frais_paid(inscription)
            except Exception as e:
                logger.exception("Erreur callback GET frais inscription #%s: %s", inscription.pk, e)
        return redirect('formations:succes', pk=inscription.pk)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = data.get('name', '')
            transaction = data.get('data', {}).get('transaction', {})
            if (
                event == 'transaction.approved'
                and inscription.statut == 'en_attente'
                and _verify_frais_payment(inscription, transaction.get('id'))
            ):
                _mark_inscription_frais_paid(inscription)
        except Exception as e:
            logger.exception("Erreur callback frais inscription #%s: %s", inscription.pk, e)
    return HttpResponse(status=200)


@csrf_exempt
def callback_formation(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation'), pk=pk)
    if request.method == 'GET':
        if inscription.statut == 'frais_payes' and _verify_formation_payment(inscription, request.GET.get('id')):
            try:
                _mark_inscription_formation_paid(inscription)
            except Exception as e:
                logger.exception("Erreur callback GET formation inscription #%s: %s", inscription.pk, e)
        return redirect('formations:succes_formation', pk=inscription.pk)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = data.get('name', '')
            transaction = data.get('data', {}).get('transaction', {})
            if (
                event == 'transaction.approved'
                and inscription.statut == 'frais_payes'
                and _verify_formation_payment(inscription, transaction.get('id'))
            ):
                _mark_inscription_formation_paid(inscription)
        except Exception as e:
            logger.exception("Erreur callback formation inscription #%s: %s", inscription.pk, e)
    return HttpResponse(status=200)


def succes_inscription(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation'), pk=pk)
    _check_inscription_access(request, inscription)
    if inscription.statut == 'en_attente':
        if _verify_frais_payment(inscription, request.GET.get('id')):
            try:
                _mark_inscription_frais_paid(inscription)
            except Exception as e:
                logger.exception("Erreur envoi facture email inscription #%s: %s", inscription.pk, e)
                messages.warning(request, "Paiement confirme, mais l'envoi automatique de la facture a echoue. Vous pouvez la telecharger depuis votre espace.")
        else:
            messages.warning(request, "Paiement en attente de confirmation FedaPay. Rechargez cette page dans quelques secondes.")
    ctx = {
        'inscription': inscription,
        'title': "Inscription confirmée !",
    }
    return render(request, 'formations/succes.html', ctx)


def succes_formation(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation'), pk=pk)
    _check_inscription_access(request, inscription)
    if inscription.statut == 'en_attente':
        messages.warning(request, "Veuillez d'abord payer les frais d'inscription.")
        return redirect('formations:paiement_frais', pk=inscription.pk)

    if inscription.statut not in Inscription.STATUTS_PAYES:
        if _verify_formation_payment(inscription, request.GET.get('id')):
            try:
                _mark_inscription_formation_paid(inscription)
            except Exception as e:
                logger.exception("Erreur envoi facture formation email inscription #%s: %s", inscription.pk, e)
                messages.warning(request, "Paiement confirme, mais l'envoi automatique de la facture formation a echoue. Vous pouvez la telecharger depuis votre espace.")
        else:
            messages.warning(request, "Paiement formation en attente de confirmation FedaPay. Rechargez cette page dans quelques secondes.")

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


@login_required
def lancer_meet_inscription(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation', 'utilisateur'), pk=pk)

    if not _can_access_meet_room(request.user, inscription):
        return HttpResponseForbidden('Acces refuse a cette session en ligne.')

    if inscription.mode_preference != 'en_ligne':
        messages.warning(request, "Cette inscription est en presentiel. Activez l'option en ligne pour utiliser Meet.")
        return redirect('formations:mes_inscriptions')

    return redirect('formations:meet_room', pk=inscription.pk)


@login_required
def meet_room(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation', 'utilisateur'), pk=pk)

    if not _can_access_meet_room(request.user, inscription):
        return HttpResponseForbidden('Acces refuse a cette session en ligne.')

    if inscription.mode_preference != 'en_ligne':
        messages.warning(request, "Cette inscription est en presentiel. Aucune salle en ligne n'est disponible.")
        return redirect('formations:mes_inscriptions')

    payload = _jitsi_embed_payload(inscription, request.user)
    if not payload.get('meet_url') or not payload.get('jitsi_domain') or not payload.get('jitsi_room_name'):
        messages.error(request, "Impossible de preparer la salle Jitsi pour cette inscription.")
        return redirect('formations:mes_inscriptions')

    context = {
        'inscription': inscription,
        'title': f"Salle en ligne - {inscription.formation.titre}",
        'is_admin_meet_view': request.user.is_staff,
        **payload,
    }
    return render(request, 'formations/meet_room.html', context)


def facture_frais_pdf(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation', 'utilisateur'), pk=pk)
    _check_inscription_access(request, inscription)

    return _build_frais_invoice_response(inscription)


def facture_formation_pdf(request, pk):
    inscription = get_object_or_404(Inscription.objects.select_related('formation', 'utilisateur'), pk=pk)
    _check_inscription_access(request, inscription)

    return _build_formation_invoice_response(inscription)

