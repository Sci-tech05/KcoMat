from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from formations.models import Inscription
from boutique.models import Commande
from .models import ProfilUtilisateur
from .forms import UserUpdateForm, ProfilUtilisateurForm, KcomatPasswordChangeForm


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
    profil, _ = ProfilUtilisateur.objects.get_or_create(utilisateur=request.user)
    inscriptions = Inscription.objects.filter(utilisateur=request.user).select_related('formation')[:10]
    commandes = Commande.objects.filter(utilisateur=request.user)[:10]
    ctx = {
        'profil': profil,
        'inscriptions': inscriptions,
        'commandes': commandes,
        'title': 'Mon espace KcoMat',
    }
    return render(request, 'accounts/dashboard.html', ctx)


@login_required
def profil(request):
    profil, _ = ProfilUtilisateur.objects.get_or_create(utilisateur=request.user)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def form_errors_to_dict(form):
        errors = {}
        for field, field_errors in form.errors.items():
            if field == '__all__':
                errors['non_field_errors'] = [str(err) for err in field_errors]
            else:
                errors[field] = [str(err) for err in field_errors]
        return errors

    user_form = UserUpdateForm(instance=request.user)
    profil_form = ProfilUtilisateurForm(instance=profil)
    password_form = KcomatPasswordChangeForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'profile':
            user_form = UserUpdateForm(request.POST, instance=request.user)
            profil_form = ProfilUtilisateurForm(request.POST, instance=profil)
            if user_form.is_valid() and profil_form.is_valid():
                user_form.save()
                profil_form.save()
                messages.success(request, 'Profil mis à jour avec succès.')
                if is_ajax:
                    return JsonResponse({
                        'ok': True,
                        'action': 'profile',
                        'message': 'Profil mis à jour avec succès.',
                    })
                return redirect('accounts:profil')
            messages.error(request, 'Veuillez corriger les champs du profil.')
            if is_ajax:
                return JsonResponse({
                    'ok': False,
                    'action': 'profile',
                    'message': 'Veuillez corriger les champs du profil.',
                    'errors': {
                        'user': form_errors_to_dict(user_form),
                        'profil': form_errors_to_dict(profil_form),
                    },
                }, status=400)

        elif action == 'password':
            password_form = KcomatPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Mot de passe modifié avec succès.')
                if is_ajax:
                    return JsonResponse({
                        'ok': True,
                        'action': 'password',
                        'message': 'Mot de passe modifié avec succès.',
                    })
                return redirect('accounts:profil')
            messages.error(request, 'Veuillez corriger les champs du mot de passe.')
            if is_ajax:
                return JsonResponse({
                    'ok': False,
                    'action': 'password',
                    'message': 'Veuillez corriger les champs du mot de passe.',
                    'errors': {
                        'password': form_errors_to_dict(password_form),
                    },
                }, status=400)

    ctx = {
        'title': 'Modifier mon profil',
        'user_form': user_form,
        'profil_form': profil_form,
        'password_form': password_form,
    }
    return render(request, 'accounts/profil.html', ctx)
