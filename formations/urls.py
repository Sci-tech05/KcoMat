from django.urls import path
from . import views

app_name = 'formations'

urlpatterns = [
    path('', views.liste_formations, name='liste'),
    path('mes-inscriptions/', views.mes_inscriptions, name='mes_inscriptions'),
    path('<slug:slug>/', views.detail_formation, name='detail'),
    path('inscription/<int:pk>/paiement-frais/', views.paiement_frais, name='paiement_frais'),
    path('inscription/<int:pk>/paiement-formation/', views.paiement_formation, name='paiement_formation'),
    path('inscription/<int:pk>/callback-frais/', views.callback_frais, name='callback_frais'),
    path('inscription/<int:pk>/callback-formation/', views.callback_formation, name='callback_formation'),
    path('inscription/<int:pk>/succes/', views.succes_inscription, name='succes'),
    path('inscription/<int:pk>/succes-formation/', views.succes_formation, name='succes_formation'),
    path('inscription/<int:pk>/facture-frais.pdf', views.facture_frais_pdf, name='facture_frais'),
    path('inscription/<int:pk>/facture-formation.pdf', views.facture_formation_pdf, name='facture_formation'),
]
