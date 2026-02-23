from django.urls import path
from . import views

app_name = 'formations'

urlpatterns = [
    path('', views.liste_formations, name='liste'),
    path('mes-inscriptions/', views.mes_inscriptions, name='mes_inscriptions'),
    path('<slug:slug>/', views.detail_formation, name='detail'),
    path('inscription/<int:pk>/paiement-frais/', views.paiement_frais, name='paiement_frais'),
    path('inscription/<int:pk>/callback-frais/', views.callback_frais, name='callback_frais'),
    path('inscription/<int:pk>/succes/', views.succes_inscription, name='succes'),
]
