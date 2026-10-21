from django.urls import path
from . import avis, views

app_name = 'core'

urlpatterns = [
    path('', views.accueil, name='accueil'),
    path('a-propos/', views.a_propos, name='a_propos'),
    path('contact/', views.contact, name='contact'),
    path('confidentialite/', views.confidentialite, name='confidentialite'),
    path('avis/<str:type_objet>/<int:pk>/', avis.donner_avis, name='donner_avis'),
]
