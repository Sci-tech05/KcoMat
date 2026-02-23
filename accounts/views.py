from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from formations.models import Inscription
from boutique.models import Commande


def connexion(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Bienvenue, {user.first_name or user.username} !")
        return redirect(request.GET.get('next', 'accounts:dashboard'))
    return render(request, 'accounts/connexion.html', {'form': form, 'title': 'Connexion'})


def inscription(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "✅ Compte créé avec succès ! Bienvenue chez KcoMat.")
        return redirect('accounts:dashboard')
    return render(request, 'accounts/inscription.html', {'form': form, 'title': 'Créer un compte'})


def deconnexion(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('core:accueil')


@login_required
def dashboard(request):
    inscriptions = Inscription.objects.filter(utilisateur=request.user).select_related('formation')[:10]
    commandes = Commande.objects.filter(utilisateur=request.user)[:10]
    ctx = {
        'inscriptions': inscriptions,
        'commandes': commandes,
        'title': 'Mon espace KcoMat',
    }
    return render(request, 'accounts/dashboard.html', ctx)
