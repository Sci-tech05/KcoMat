from django.urls import path
from . import paiement, views

app_name = 'services'

urlpatterns = [
    path('', views.liste_services, name='liste'),
    path('consultation/<int:pk>/paiement/', paiement.paiement_consultation, name='paiement_consultation'),
    path('consultation/<int:pk>/callback/', paiement.callback_consultation, name='callback_consultation'),
    path('consultation/<int:pk>/confirmation/', paiement.confirmation_consultation, name='confirmation_consultation'),
    path('consultation/<int:pk>/facture.pdf', paiement.facture_consultation, name='facture_consultation'),
    path('<slug:slug>/', views.detail_service, name='detail'),
]
