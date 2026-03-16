import json
import logging
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.core.mail import EmailMessage
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Produit, CategorieProduit, Panier, PanierItem, Commande, CommandeItem
from .forms import CommandeForm
from core.pdf_invoices import build_invoice_response


logger = logging.getLogger(__name__)


def _get_panier(request):
    """Récupère ou crée le panier de la session/utilisateur."""
    if not request.session.session_key:
        request.session.create()
    if request.user.is_authenticated:
        panier, _ = Panier.objects.get_or_create(utilisateur=request.user)
    else:
        panier, _ = Panier.objects.get_or_create(session_key=request.session.session_key, utilisateur=None)
    return panier


def _finalize_paid_commande(commande, request=None):
    """Applique les effets de bord une seule fois quand une commande passe en payee."""
    # Decrementer le stock a la validation du paiement (et non au checkout).
    for order_item in commande.items.select_related('produit').all():
        if not order_item.produit:
            continue
        product = order_item.produit
        product.stock = max(product.stock - order_item.quantite, 0)
        product.save(update_fields=['stock'])

    # Retirer du panier uniquement les quantites correspondant a cette commande.
    paniers = []
    if commande.utilisateur_id:
        panier_user = Panier.objects.filter(utilisateur=commande.utilisateur).first()
        if panier_user:
            paniers.append(panier_user)
    elif request is not None and request.session.session_key:
        panier_session = Panier.objects.filter(session_key=request.session.session_key, utilisateur=None).first()
        if panier_session:
            paniers.append(panier_session)

    if not paniers:
        return

    ordered_quantities = {}
    for order_item in commande.items.all():
        if order_item.produit_id:
            ordered_quantities[order_item.produit_id] = ordered_quantities.get(order_item.produit_id, 0) + order_item.quantite

    for panier in paniers:
        panier_items = panier.items.filter(produit_id__in=list(ordered_quantities.keys())).select_related('produit')
        for panier_item in panier_items:
            qty_to_remove = ordered_quantities.get(panier_item.produit_id, 0)
            if qty_to_remove <= 0:
                continue
            if panier_item.quantite <= qty_to_remove:
                panier_item.delete()
            else:
                panier_item.quantite -= qty_to_remove
                panier_item.save(update_fields=['quantite'])


def _build_commande_invoice_response(commande):
    items = []
    for item in commande.items.all():
        image_path = ''
        if item.produit and item.produit.image:
            try:
                image_path = item.produit.image.path
            except Exception:
                image_path = ''
        items.append({
            'description': item.nom_produit,
            'image_path': image_path,
            'quantity': item.quantite,
            'unit_price': item.prix_unitaire,
            'subtotal': item.sous_total(),
        })

    return build_invoice_response(
        filename=f'facture-commande-{commande.pk}.pdf',
        title='Facture commande',
        invoice_number=f'CMD-{commande.pk:06d}',
        customer_name=f'{commande.prenom} {commande.nom}',
        customer_email=commande.email,
        customer_phone=commande.telephone,
        customer_address=commande.adresse_livraison,
        status_label=commande.get_statut_display(),
        items=items,
        total_amount=commande.montant_total,
        note='Merci pour votre achat chez KcoMat.',
    )


def _send_commande_invoice_email(commande):
    recipient = (commande.email or '').strip()
    if not recipient:
        return

    invoice_response = _build_commande_invoice_response(commande)
    invoice_filename = f'facture-commande-{commande.pk}.pdf'
    subject = f'KcoMat - Votre facture commande #{commande.pk}'
    body = (
        f"Bonjour {commande.prenom} {commande.nom},\n\n"
        f"Votre paiement a ete confirme.\n"
        f"Veuillez trouver votre facture en piece jointe.\n\n"
        f"Commande: #{commande.pk}\n"
        f"Montant: {commande.montant_total} FCFA\n\n"
        "Merci pour votre confiance.\n"
        "KcoMat"
    )

    message = EmailMessage(
        subject=subject,
        body=body,
        to=[recipient],
    )
    message.attach(invoice_filename, invoice_response.content, 'application/pdf')
    message.send(fail_silently=False)


def liste_produits(request):
    categories = CategorieProduit.objects.all()
    cat_slug = request.GET.get('categorie', '')
    search = request.GET.get('q', '')
    produits = Produit.objects.filter(actif=True)
    if cat_slug:
        produits = produits.filter(categorie__slug=cat_slug)
    if search:
        produits = produits.filter(nom__icontains=search)
    ctx = {
        'produits': produits,
        'categories': categories,
        'cat_active': cat_slug,
        'search': search,
        'title': 'Boutique — Composants Électroniques',
    }
    return render(request, 'boutique/liste.html', ctx)


def detail_produit(request, slug):
    produit = get_object_or_404(Produit, slug=slug, actif=True)
    produits_similaires = Produit.objects.filter(
        actif=True, categorie=produit.categorie
    ).exclude(pk=produit.pk)[:4]
    ctx = {
        'produit': produit,
        'produits_similaires': produits_similaires,
        'title': produit.nom,
    }
    return render(request, 'boutique/detail.html', ctx)


@require_POST
def ajouter_panier(request, slug):
    """Ajoute un produit au panier (HTMX ou normal)."""
    if not request.user.is_authenticated:
        messages.warning(request, "🔒 Connectez-vous d'abord pour ajouter un produit au panier !")
        referer = request.META.get('HTTP_REFERER', reverse('boutique:liste'))
        if request.htmx:
            response = HttpResponse()
            response['HX-Redirect'] = referer
            return response
        return redirect(referer)

    produit = get_object_or_404(Produit, slug=slug, actif=True)
    quantite = int(request.POST.get('quantite', 1))
    panier = _get_panier(request)
    item, created = PanierItem.objects.get_or_create(panier=panier, produit=produit)
    if not created:
        item.quantite += quantite
    else:
        item.quantite = quantite
    if item.quantite > produit.stock:
        item.quantite = produit.stock
    item.save()
    messages.success(request, f"✅ {produit.nom} ajouté au panier !")
    if request.htmx:
        response = HttpResponse()
        response['HX-Redirect'] = reverse('boutique:panier')
        return response
    return redirect('boutique:panier')


def voir_panier(request):
    panier = _get_panier(request)
    items = panier.items.select_related('produit').all()
    ctx = {
        'panier': panier,
        'items': items,
        'title': 'Mon Panier',
    }
    return render(request, 'boutique/panier.html', ctx)


@require_POST
def supprimer_item(request, item_id):
    panier = _get_panier(request)
    PanierItem.objects.filter(pk=item_id, panier=panier).delete()
    messages.info(request, "Article retiré du panier.")
    return redirect('boutique:panier')


@require_POST
def modifier_quantite(request, item_id):
    panier = _get_panier(request)
    quantite = int(request.POST.get('quantite', 1))
    item = get_object_or_404(PanierItem, pk=item_id, panier=panier)
    if quantite < 1:
        item.delete()
    else:
        item.quantite = min(quantite, item.produit.stock)
        item.save()
    return redirect('boutique:panier')


def checkout(request):
    panier = _get_panier(request)
    if panier.nombre_articles() == 0:
        messages.warning(request, "Votre panier est vide.")
        return redirect('boutique:liste')

    if request.method == 'POST':
        form = CommandeForm(request.POST)
    elif request.user.is_authenticated:
        profil = getattr(request.user, 'profil_kcomat', None)
        last_commande = Commande.objects.filter(utilisateur=request.user).order_by('-created_at').first()
        form = CommandeForm(initial={
            'prenom': request.user.first_name,
            'nom': request.user.last_name,
            'email': request.user.email,
            'telephone': getattr(profil, 'telephone', '') or (last_commande.telephone if last_commande else ''),
            'adresse_livraison': getattr(profil, 'adresse', '') or (last_commande.adresse_livraison if last_commande else ''),
            'ville': last_commande.ville if last_commande else '',
        })
    else:
        form = CommandeForm()

    if request.method == 'POST' and form.is_valid():
        commande = form.save(commit=False)
        if request.user.is_authenticated:
            commande.utilisateur = request.user
        commande.montant_total = panier.total()
        commande.save()
        # Créer les items de commande
        for item in panier.items.select_related('produit').all():
            CommandeItem.objects.create(
                commande=commande,
                produit=item.produit,
                nom_produit=item.produit.nom,
                prix_unitaire=item.produit.prix,
                quantite=item.quantite,
            )
        # Initier paiement Fedapay
        return redirect('boutique:paiement', pk=commande.pk)
    ctx = {
        'panier': panier,
        'form': form,
        'title': 'Finaliser ma commande',
    }
    return render(request, 'boutique/checkout.html', ctx)


def paiement_commande(request, pk):
    """Initie le paiement de la commande via l'endpoint API local (qui utilise FedaPay SDK via PHP)."""
    commande = get_object_or_404(Commande, pk=pk)
    if commande.statut not in ['en_attente']:
        messages.info(request, "Cette commande a déjà été traitée.")
        return redirect('boutique:liste')

    app_url = settings.FEDAPAY_APP_URL or request.build_absolute_uri('/').rstrip('/')
    callback_url = f"{app_url}/boutique/commande/{commande.pk}/callback/"
    success_url = settings.FEDAPAY_SUCCESS_URL or f"{app_url}/boutique/commande/{commande.pk}/succes/"
    cancel_url = settings.FEDAPAY_CANCEL_URL or f"{app_url}/boutique/panier/"
    
    # Appeler l'endpoint API local pour créer la transaction FedaPay
    api_url = request.build_absolute_uri('/') + 'api/create-transaction/'
    
    transaction_payload = {
        'amount': int(commande.montant_total),
        'description': f"Commande KcoMat #{commande.pk}",
        'currency': settings.PAYMENT_CONFIG['currency'],
        'country': settings.PAYMENT_CONFIG['country'],
        'customer': {
            'firstname': commande.prenom,
            'lastname': commande.nom,
            'email': commande.email,
            'phone': commande.telephone,
        },
        'callback_url': callback_url,
        'metadata': {
            'source': 'KcoMat',
            'type': 'commande',
            'commande_id': str(commande.pk),
            'success_url': success_url,
            'cancel_url': cancel_url,
        }
    }

    try:
        resp = requests.post(api_url, json=transaction_payload, timeout=10)
        data = resp.json()
        
        if not data.get('success') or not data.get('transaction_id'):
            logger.warning(
                "KcoMat API create transaction failed (boutique): status=%s response=%s",
                resp.status_code,
                data
            )
            messages.error(request, "Impossible de créer la transaction de paiement: " + data.get('error', 'Erreur inconnue'))
        else:
            # Sauvegarde l'ID de transaction FedaPay
            transaction_id = data['transaction_id']
            token = data['token']
            checkout_url = data.get('checkout_url', '')
            
            commande.fedapay_transaction_id = str(transaction_id)
            commande.save(update_fields=['fedapay_transaction_id'])
            
            logger.info("FedaPay transaction created (boutique): %s", transaction_id)
            
            # Passer le token au template pour Checkout.js
            ctx = {
                'commande': commande,
                'title': 'Paiement de la commande',
                'fedapay_public_key': settings.FEDAPAY_PUBLIC_KEY,
                'transaction_id': transaction_id,
                'token': token,
                'checkout_url': checkout_url,
                'sandbox': settings.FEDAPAY_SANDBOX,
            }
            return render(request, 'boutique/paiement_checkout.html', ctx)
            
    except requests.RequestException as e:
        logger.exception("KcoMat API HTTP error (boutique): %s", e)
        messages.error(request, "Erreur réseau lors de la connexion au service de paiement.")
    except Exception as e:
        logger.exception("Unexpected error creating transaction (boutique): %s", e)
        messages.error(request, "Une erreur inattendue est survenue lors de l'initialisation du paiement.")

    # Fallback: rediriger vers le panier
    return redirect('boutique:panier')


@csrf_exempt
def callback_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = data.get('name', '')
            transaction = data.get('data', {}).get('transaction', {})
            if event == 'transaction.approved' and transaction.get('status') == 'approved' and commande.statut != 'payee':
                commande.statut = 'payee'
                commande.payee_le = timezone.now()
                commande.save(update_fields=['statut', 'payee_le'])
                _finalize_paid_commande(commande)
                _send_commande_invoice_email(commande)
        except Exception as e:
            logger.exception("Erreur callback commande #%s: %s", commande.pk, e)
    return HttpResponse(status=200)


def succes_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if commande.statut == 'en_attente':
        commande.statut = 'payee'
        commande.payee_le = timezone.now()
        commande.save(update_fields=['statut', 'payee_le'])
        _finalize_paid_commande(commande, request=request)
        try:
            _send_commande_invoice_email(commande)
        except Exception as e:
            logger.exception("Erreur envoi facture email commande #%s: %s", commande.pk, e)
            messages.warning(request, "Paiement confirme, mais l'envoi automatique de la facture a echoue. Vous pouvez la telecharger depuis votre espace.")
    ctx = {
        'commande': commande,
        'title': 'Commande confirmée !',
    }
    return render(request, 'boutique/succes_commande.html', ctx)


def facture_panier_pdf(request):
    panier = _get_panier(request)
    items_qs = panier.items.select_related('produit').all()
    if not items_qs:
        return HttpResponse('Panier vide.', status=400)

    items = []
    for item in items_qs:
        image_path = ''
        if item.produit.image:
            try:
                image_path = item.produit.image.path
            except Exception:
                image_path = ''
        items.append({
            'description': item.produit.nom,
            'image_path': image_path,
            'quantity': item.quantite,
            'unit_price': item.produit.prix,
            'subtotal': item.sous_total(),
        })

    customer_name = 'Client KcoMat'
    customer_email = ''
    customer_phone = ''
    customer_address = ''
    if request.user.is_authenticated:
        full_name = f"{request.user.first_name} {request.user.last_name}".strip()
        customer_name = full_name or request.user.username
        customer_email = request.user.email
        profil = getattr(request.user, 'profil_kcomat', None)
        if profil:
            customer_phone = profil.telephone or ''
            customer_address = profil.adresse or ''

    return build_invoice_response(
        filename='facture-panier-kcomat.pdf',
        title='Facture pro forma (Panier)',
        invoice_number=f'PAN-{panier.pk or 0}-{timezone.now().strftime("%Y%m%d%H%M")}',
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        customer_address=customer_address,
        status_label='Non payée',
        items=items,
        total_amount=panier.total(),
        note='Cette facture est une estimation avant validation definitive de la commande.',
    )


def facture_commande_pdf(request, pk):
    commande = get_object_or_404(Commande.objects.prefetch_related('items'), pk=pk)

    if commande.utilisateur_id and (not request.user.is_authenticated or (request.user != commande.utilisateur and not request.user.is_staff)):
        return HttpResponseForbidden('Acces refuse a cette facture.')

    return _build_commande_invoice_response(commande)
