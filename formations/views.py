import json
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Formation, Inscription, CategorieFormation
from .forms import InscriptionForm


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
    form = InscriptionForm(request.POST or None)
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
    """Initie le paiement des frais d'inscription (2000 FCFA) via Fedapay."""
    inscription = get_object_or_404(Inscription, pk=pk)
    if inscription.statut != 'en_attente':
        messages.warning(request, "Cette inscription a déjà été traitée.")
        return redirect('formations:liste')

    fedapay_api = settings.FEDAPAY_SECRET_KEY
    sandbox = settings.FEDAPAY_SANDBOX
    base_url = "https://sandbox-api.fedapay.com/v1" if sandbox else "https://api.fedapay.com/v1"
    callback_url = request.build_absolute_uri(f'/formations/callback-frais/{inscription.pk}/')
    return_url = request.build_absolute_uri(f'/formations/succes/{inscription.pk}/')

    payload = {
        "description": f"Frais d'inscription KcoMat — {inscription.formation.titre}",
        "amount": settings.KCOMAT_INFO['frais_inscription'],
        "currency": {"iso": "XOF"},
        "callback_url": callback_url,
        "customer": {
            "firstname": inscription.prenom,
            "lastname": inscription.nom,
            "email": inscription.email,
            "phone_number": {"number": inscription.telephone, "country": "bj"},
        },
    }
    headers = {"Authorization": f"Bearer {fedapay_api}", "Content-Type": "application/json"}

    try:
        resp = requests.post(f"{base_url}/transactions", json=payload, headers=headers, timeout=15)
        data = resp.json()
        transaction = data.get("v1/transaction", {})
        transaction_id = transaction.get("id", "")
        payment_url_response = requests.post(
            f"{base_url}/transactions/{transaction_id}/token",
            headers=headers, timeout=15
        )
        token_data = payment_url_response.json()
        payment_url = token_data.get("token", {}).get("token", "")
        if payment_url:
            pay_url = f"https://checkout{'.' if not sandbox else '-sandbox.'}fedapay.com/checkout/{payment_url}"
            inscription.fedapay_frais_id = str(transaction_id)
            inscription.save(update_fields=['fedapay_frais_id'])
            return redirect(pay_url)
    except Exception as e:
        pass

    ctx = {
        'inscription': inscription,
        'frais': settings.KCOMAT_INFO['frais_inscription'],
        'title': "Paiement des frais d'inscription",
        'fedapay_public_key': settings.FEDAPAY_PUBLIC_KEY,
        'sandbox': settings.FEDAPAY_SANDBOX,
    }
    return render(request, 'formations/paiement.html', ctx)


@csrf_exempt
def callback_frais(request, pk):
    """Webhook Fedapay — confirmation paiement frais d'inscription."""
    inscription = get_object_or_404(Inscription, pk=pk)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = data.get('name', '')
            transaction = data.get('data', {}).get('transaction', {})
            if event == 'transaction.approved' and transaction.get('status') == 'approved':
                inscription.statut = 'frais_payes'
                inscription.frais_payes_le = timezone.now()
                inscription.save(update_fields=['statut', 'frais_payes_le'])
        except Exception:
            pass
    return HttpResponse(status=200)


def succes_inscription(request, pk):
    inscription = get_object_or_404(Inscription, pk=pk)
    if inscription.statut == 'en_attente':
        # Marquer comme frais payés si on arrive ici depuis le checkout
        inscription.statut = 'frais_payes'
        inscription.frais_payes_le = timezone.now()
        inscription.save(update_fields=['statut', 'frais_payes_le'])
    ctx = {
        'inscription': inscription,
        'title': "Inscription confirmée !",
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
