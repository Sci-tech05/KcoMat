"""Connexion avec Google (django-allauth) : règles propres à KcoMat."""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect


class AdaptateurGoogle(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        # Un compte administrateur peut se connecter au site avec Google comme tout le monde :
        # l'administration reste protégée par le code de vérification envoyé par e-mail
        # (core.admin_security.AdminSecurityMiddleware), demandé quelle que soit la méthode de connexion.
        utilisateur = sociallogin.user
        if utilisateur.pk and utilisateur.is_staff:
            emails_google = {e.email.lower() for e in sociallogin.email_addresses if e.verified}
            if (utilisateur.email or '').lower() in emails_google:
                # E-mail confirmé par Google : allauth n'efface plus le mot de passe du compte
                # (il le fait pour une adresse non vérifiée), indispensable pour entrer dans l'admin.
                adresse = EmailAddress.objects.filter(user=utilisateur, email__iexact=utilisateur.email).first()
                if adresse is None:
                    EmailAddress.objects.create(user=utilisateur, email=utilisateur.email, verified=True,
                                                primary=not EmailAddress.objects.filter(user=utilisateur, primary=True).exists())
                elif not adresse.verified:
                    adresse.verified = True
                    adresse.save(update_fields=['verified'])
        super().pre_social_login(request, sociallogin)

    def save_user(self, request, sociallogin, form=None):
        """Première connexion Google : compte créé avec le prénom, le nom et l'e-mail fournis par Google."""
        utilisateur = super().save_user(request, sociallogin, form)
        request._kx_inscription_google = True
        messages.success(request, "✅ Compte créé avec Google ! Bienvenue chez KcoMat.")
        return utilisateur

    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        # Annulation ou refus côté Google : retour à la page de connexion du site avec un message clair
        messages.error(request, "La connexion avec Google n'a pas abouti. Réessayez ou utilisez votre mot de passe.")
        raise ImmediateHttpResponse(redirect('accounts:connexion'))


class AdaptateurCompte(DefaultAccountAdapter):

    def post_login(self, request, user, *, signup, **kwargs):
        reponse = super().post_login(request, user, signup=signup, **kwargs)
        # Posé APRÈS allauth : le rendu de son message de connexion passe par les context
        # processors, qui consomment « proposer_notifications ».
        if signup:
            request.session['proposer_notifications'] = True   # même accueil qu'une inscription classique
        return reponse

    def add_message(self, request, level, message_template=None, message_context=None, extra_tags="", message=None):
        # 1re connexion Google : un seul message de bienvenue (le nôtre) au lieu de « Connexion réussie »
        if message_template == "account/messages/logged_in.txt" and getattr(request, "_kx_inscription_google", False):
            return
        super().add_message(request, level, message_template, message_context, extra_tags, message)
