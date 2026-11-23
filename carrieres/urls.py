from django.urls import path
from . import paiement, views

app_name = 'carrieres'

urlpatterns = [
    path('', views.liste_offres, name='liste'),
    path('paiement/<str:code>/', paiement.paiement_frais, name='paiement_frais'),
    path('paiement/<str:code>/callback/', paiement.callback_frais, name='callback_frais'),
    path('paiement/<str:code>/facture.pdf', paiement.facture_frais, name='facture_frais'),
    path('<slug:slug>/', views.detail_offre, name='detail'),
]
