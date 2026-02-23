from django.urls import path
from . import views

app_name = 'carrieres'

urlpatterns = [
    path('', views.liste_offres, name='liste'),
    path('<slug:slug>/', views.detail_offre, name='detail'),
]
