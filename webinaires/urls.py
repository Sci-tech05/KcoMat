from django.urls import path

from . import paiement, views

app_name = 'webinaires'

urlpatterns = [
    path('', views.liste, name='liste'),
    path('attestation/<str:code>/', views.verifier_attestation, name='verifier'),
    path('attestation-paiement/<int:pk>/callback/', paiement.callback_attestation, name='callback_attestation'),
    path('<slug:slug>/', views.detail, name='detail'),
    path('<slug:slug>/inscription/', views.inscrire, name='inscrire'),
    path('<slug:slug>/salle/', views.salle, name='salle'),
    path('<slug:slug>/agenda.ics', views.agenda, name='agenda'),
    path('<slug:slug>/attestation.pdf', views.attestation, name='attestation'),
    path('<slug:slug>/attestation/paiement/', paiement.paiement_attestation, name='paiement_attestation'),
]
