import hashlib

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.cache import cache
from django.utils.http import url_has_allowed_host_and_scheme
from core.admin_security import _get_client_ip

# Anti-essais en série : au-delà de 5 échecs pour un même identifiant, pause de 15 minutes
ESSAIS_MAX = 5
PAUSE_SECONDES = 15 * 60
from formations.models import Inscription
from boutique.models import Commande
from webinaires.views import contexte_cartes
from webinaires.models import Webinaire
from .models import ProfilUtilisateur
from .forms import InscriptionForm, UserUpdateForm, ProfilUtilisateurForm, KcomatPasswordChangeForm


def _page_suivante(request, defaut='accounts:dashboard'):
    """Adresse « next » seulement si elle reste sur ce site (évite les redirections vers un site pirate)."""
    suivante = request.POST.get('next') or request.GET.get('next')
    if suivante and url_has_allowed_host_and_scheme(
        suivante, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return suivante
    return defaut


def connexion(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    donnees = None
    if request.method == 'POST':
        donnees = request.POST.copy()
        identifiant = donnees.get('username', '').strip()
        # Connexion possible avec l'adresse e-mail à la place du nom d'utilisateur
        if '@' in identifiant:
            compte = User.objects.filter(email__iexact=identifiant).order_by('-last_login').first()
            if compte:
                donnees['username'] = compte.get_username()
    form = AuthenticationForm(request, data=donnees)
    bloque = False
    if request.method == 'POST':
        empreinte = hashlib.sha256(('%s|%s' % (_get_client_ip(request), donnees.get('username', '').strip().lower())).encode()).hexdigest()
        cle = 'kx-connexion:' + empreinte
        essais = cache.get(cle, 0)
        if essais >= ESSAIS_MAX:
            bloque = True
        elif form.is_valid():
            cache.delete(cle)
        else:
            cache.set(cle, essais + 1, PAUSE_SECONDES)
    if bloque:
        form = AuthenticationForm(request)
        messages.error(request, "Trop de tentatives de connexion. Réessayez dans 15 minutes ou utilisez « Mot de passe oublié ».")
    elif request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Bienvenue, {user.first_name or user.username} !")
        return redirect(_page_suivante(request))
    return render(request, 'accounts/connexion.html', {
        'form': form, 'title': 'Connexion', 'next': _page_suivante(request, ''),
    })


def inscription(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = InscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        request.session['proposer_notifications'] = True  # propose l'abonnement aux notifications
        messages.success(request, "✅ Compte créé avec succès ! Bienvenue chez KcoMat.")
        return redirect(_page_suivante(request))
    return render(request, 'accounts/inscription.html', {
        'form': form, 'title': 'Créer un compte', 'next': _page_suivante(request, ''),
    })


def deconnexion(request):
    """Déconnexion uniquement par formulaire (POST + jeton CSRF) : un simple lien ou une
    image piégée sur un autre site ne peut plus déconnecter le client à son insu."""
    if request.method == 'POST':
        logout(request)
        messages.info(request, "Vous avez été déconnecté.")
        return redirect('core:accueil')
    if not request.user.is_authenticated:
        return redirect('core:accueil')
    return render(request, 'accounts/deconnexion.html', {'title': 'Déconnexion'})


@login_required
def dashboard(request):
    profil, _ = ProfilUtilisateur.objects.get_or_create(utilisateur=request.user)
    inscriptions = Inscription.objects.filter(utilisateur=request.user).select_related('formation')[:10]
    commandes = Commande.objects.filter(utilisateur=request.user)[:10]
    mes_webinaires = contexte_cartes(request, list(
        Webinaire.objects.filter(participations__utilisateur=request.user).order_by('-date_debut')[:6]))
    ctx = {
        'profil': profil,
        'mes_webinaires': mes_webinaires,
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
