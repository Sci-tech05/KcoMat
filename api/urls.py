from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('create-transaction/', views.create_transaction, name='create_transaction'),
]
