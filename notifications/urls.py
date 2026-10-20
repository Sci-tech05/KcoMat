from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('abonnement/', views.abonnement, name='abonnement'),
    path('desabonnement/', views.desabonnement, name='desabonnement'),
    path('renouvellement/', views.renouvellement, name='renouvellement'),
]
