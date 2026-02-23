from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.liste_services, name='liste'),
    path('<slug:slug>/', views.detail_service, name='detail'),
]
