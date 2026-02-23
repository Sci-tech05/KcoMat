import json
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Produit, CategorieProduit, Panier, PanierItem, Commande, CommandeItem
from .forms import CommandeForm


def _get_panier(request):
    """Récupère ou crée le panier de la session/utilisateur."""
    if not request.session.session_key:
        request.session.create()
    if request.user.is_authenticated:
        panier, _ = Panier.objects.get_or_create(utilisateur=request.user)
    else:
        panier, _ = Panier.objects.get_or_create(session_key=request.session.session_key, utilisateur=None)
    return panier


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
    form = CommandeForm(request.POST or None)
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
            # Décrémenter le stock
            item.produit.stock -= item.quantite
            item.produit.save(update_fields=['stock'])
        # Vider le panier
        panier.items.all().delete()
        # Initier paiement Fedapay
        return redirect('boutique:paiement', pk=commande.pk)
    ctx = {
        'panier': panier,
        'form': form,
        'title': 'Finaliser ma commande',
    }
    return render(request, 'boutique/checkout.html', ctx)


def paiement_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if commande.statut not in ['en_attente']:
        messages.info(request, "Cette commande a déjà été traitée.")
        return redirect('boutique:liste')

    fedapay_api = settings.FEDAPAY_SECRET_KEY
    sandbox = settings.FEDAPAY_SANDBOX
    base_url = "https://sandbox-api.fedapay.com/v1" if sandbox else "https://api.fedapay.com/v1"
    callback_url = request.build_absolute_uri(f'/boutique/callback/{commande.pk}/')
    return_url = request.build_absolute_uri(f'/boutique/commande/{commande.pk}/succes/')

    payload = {
        "description": f"Commande KcoMat #{commande.pk}",
        "amount": int(commande.montant_total),
        "currency": {"iso": "XOF"},
        "callback_url": callback_url,
        "customer": {
            "firstname": commande.prenom,
            "lastname": commande.nom,
            "email": commande.email,
            "phone_number": {"number": commande.telephone, "country": "bj"},
        },
    }
    headers = {"Authorization": f"Bearer {fedapay_api}", "Content-Type": "application/json"}
    try:
        resp = requests.post(f"{base_url}/transactions", json=payload, headers=headers, timeout=15)
        data = resp.json()
        transaction = data.get("v1/transaction", {})
        transaction_id = transaction.get("id", "")
        token_resp = requests.post(
            f"{base_url}/transactions/{transaction_id}/token",
            headers=headers, timeout=15
        )
        token_data = token_resp.json()
        payment_url = token_data.get("token", {}).get("token", "")
        if payment_url:
            pay_url = f"https://checkout{'.' if not sandbox else '-sandbox.'}fedapay.com/checkout/{payment_url}"
            commande.fedapay_transaction_id = str(transaction_id)
            commande.save(update_fields=['fedapay_transaction_id'])
            return redirect(pay_url)
    except Exception:
        pass

    ctx = {
        'commande': commande,
        'title': 'Paiement de la commande',
        'fedapay_public_key': settings.FEDAPAY_PUBLIC_KEY,
        'sandbox': settings.FEDAPAY_SANDBOX,
    }
    return render(request, 'boutique/paiement.html', ctx)


@csrf_exempt
def callback_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = data.get('name', '')
            transaction = data.get('data', {}).get('transaction', {})
            if event == 'transaction.approved' and transaction.get('status') == 'approved':
                commande.statut = 'payee'
                commande.payee_le = timezone.now()
                commande.save(update_fields=['statut', 'payee_le'])
        except Exception:
            pass
    return HttpResponse(status=200)


def succes_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if commande.statut == 'en_attente':
        commande.statut = 'payee'
        commande.payee_le = timezone.now()
        commande.save(update_fields=['statut', 'payee_le'])
    ctx = {
        'commande': commande,
        'title': 'Commande confirmée !',
    }
    return render(request, 'boutique/succes_commande.html', ctx)
