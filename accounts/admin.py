from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib import admin

# Connexion Google : l'application est configurée dans settings.py (.env) et aucun jeton n'est conservé,
# donc la section « Comptes sociaux » d'allauth n'a rien à faire dans l'admin.
for modele in (SocialApp, SocialAccount, SocialToken):
    if admin.site.is_registered(modele):
        admin.site.unregister(modele)
