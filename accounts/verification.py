"""Confirmation de l'adresse e-mail des comptes créés par l'inscription classique.

Un lien signé (valable EMAIL_CONFIRMATION_JOURS) est envoyé à l'inscription et à chaque changement
d'adresse ; le cliquer marque l'adresse « vérifiée » (allauth.account.models.EmailAddress).
Seule une adresse vérifiée permet à « Continuer avec Google » de se rattacher à un compte existant
(accounts.adapters.AdaptateurGoogle) : sans cela, quelqu'un pourrait créer un compte avec l'adresse
d'une autre personne et y garder l'accès une fois qu'elle s'y connecte avec Google.
"""
import logging

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetConfirmView
from django.core import signing
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

SEL = 'kcomat-confirmation-email'


def email_confirme(user):
    email = (user.email or '').strip()
    return bool(email) and EmailAddress.objects.filter(user=user, email__iexact=email, verified=True).exists()


def marquer_confirme(user):
    """Adresse actuelle du compte = vérifiée et principale ; les anciennes adresses sont oubliées
    (allauth les utiliserait sinon pour rattacher une connexion Google à ce compte)."""
    email = (user.email or '').strip().lower()
    if not email:
        return
    EmailAddress.objects.filter(user=user).exclude(email__iexact=email).delete()
    adresse = EmailAddress.objects.filter(user=user, email__iexact=email).first()
    if adresse is None:
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    elif not (adresse.verified and adresse.primary):
        adresse.verified, adresse.primary = True, True
        adresse.save(update_fields=['verified', 'primary'])


def adresse_a_confirmer(user):
    """Nouvelle adresse (inscription ou changement) : enregistrée comme non vérifiée."""
    email = (user.email or '').strip().lower()
    EmailAddress.objects.filter(user=user).exclude(email__iexact=email).delete()
    if email:
        EmailAddress.objects.update_or_create(user=user, email=email, defaults={'verified': False, 'primary': True})


def envoyer_confirmation(request, user):
    """Envoie le lien de confirmation. Retourne True si l'e-mail est parti."""
    email = (user.email or '').strip().lower()
    if not email:
        return False
    jeton = signing.dumps({'u': user.pk, 'e': email}, salt=SEL)
    ctx = {
        'user': user,
        'lien': request.build_absolute_uri(reverse('accounts:confirmer_email', args=[jeton])),
        'jours': settings.EMAIL_CONFIRMATION_JOURS,
    }
    message = EmailMultiAlternatives(
        subject='KcoMat — Confirmez votre adresse e-mail',
        body=render_to_string('accounts/emails/confirmer_email.txt', ctx),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    message.attach_alternative(render_to_string('accounts/emails/confirmer_email.html', ctx), 'text/html')
    try:
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Envoi du lien de confirmation impossible (compte %s)", user.pk)
        return False
    return True


def confirmer_email(request, jeton):
    try:
        donnees = signing.loads(jeton, salt=SEL, max_age=settings.EMAIL_CONFIRMATION_JOURS * 24 * 3600)
    except signing.SignatureExpired:
        messages.error(request, "Ce lien de confirmation a expiré. Demandez-en un nouveau depuis votre espace.")
        return redirect('accounts:dashboard')
    except signing.BadSignature:
        messages.error(request, "Ce lien de confirmation n'est pas valide.")
        return redirect('core:accueil')
    user = User.objects.filter(pk=donnees.get('u'), is_active=True).first()
    # Le lien ne vaut que pour l'adresse à laquelle il a été envoyé (pas après un changement d'adresse)
    if user is None or (user.email or '').strip().lower() != donnees.get('e'):
        messages.error(request, "Ce lien de confirmation ne correspond plus à l'adresse de votre compte.")
        return redirect('core:accueil')
    marquer_confirme(user)
    messages.success(request, "✅ Adresse e-mail confirmée. Merci !")
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return redirect('accounts:connexion')


class MotDePasseNouveauView(PasswordResetConfirmView):
    """Le lien « Mot de passe oublié » arrive dans la boîte de l'adresse du compte : le suivre jusqu'au
    bout prouve qu'on la contrôle. C'est aussi la voie sûre pour reprendre un compte créé par un tiers
    avec votre adresse (l'ancien mot de passe ne fonctionne plus et les autres sessions sont fermées)."""

    def form_valid(self, form):
        response = super().form_valid(form)
        marquer_confirme(form.user)
        return response


@login_required
@require_POST
def renvoyer_confirmation(request):
    user = request.user
    if email_confirme(user):
        messages.info(request, "Votre adresse e-mail est déjà confirmée.")
        return redirect('accounts:dashboard')
    delai = max(0, settings.EMAIL_CONFIRMATION_DELAI_RENVOI)
    if delai and not cache.add(f'kx-confirmation-email:{user.pk}', 1, delai):
        messages.warning(request, f"Un e-mail vient d'être envoyé. Patientez {delai} secondes avant d'en redemander un.")
    elif envoyer_confirmation(request, user):
        messages.success(request, f"Un nouveau lien de confirmation a été envoyé à {user.email}.")
    else:
        messages.error(request, "L'e-mail n'a pas pu être envoyé. Réessayez dans quelques minutes.")
    return redirect('accounts:dashboard')
