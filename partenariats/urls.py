from django.urls import path
from . import views

app_name = 'partenariats'

urlpatterns = [
    path('', views.partenariats, name='index'),
]
