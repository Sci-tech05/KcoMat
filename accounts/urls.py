from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views
from .forms import MotDePasseOublieForm

app_name = 'accounts'

urlpatterns = [
    path('connexion/', views.connexion, name='connexion'),
    path('inscription/', views.inscription, name='inscription'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profil/', views.profil, name='profil'),

    # Mot de passe oublié : demande → e-mail avec lien → nouveau mot de passe
    path('mot-de-passe-oublie/', auth_views.PasswordResetView.as_view(
        template_name='accounts/mdp_oublie.html',
        form_class=MotDePasseOublieForm,
        email_template_name='accounts/emails/mdp_oublie.txt',
        html_email_template_name='accounts/emails/mdp_oublie.html',
        subject_template_name='accounts/emails/mdp_oublie_sujet.txt',
        success_url=reverse_lazy('accounts:mdp_oublie_envoye'),
    ), name='mdp_oublie'),
    path('mot-de-passe-oublie/envoye/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/mdp_oublie_envoye.html',
    ), name='mdp_oublie_envoye'),
    path('mot-de-passe/nouveau/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/mdp_nouveau.html',
        success_url=reverse_lazy('accounts:mdp_modifie'),
    ), name='mdp_nouveau'),
    path('mot-de-passe/modifie/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/mdp_modifie.html',
    ), name='mdp_modifie'),
]
