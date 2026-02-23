from django.urls import path
from . import views

app_name = 'boutique'

urlpatterns = [
    path('', views.liste_produits, name='liste'),
    path('panier/', views.voir_panier, name='panier'),
    path('panier/ajouter/<slug:slug>/', views.ajouter_panier, name='ajouter'),
    path('panier/supprimer/<int:item_id>/', views.supprimer_item, name='supprimer_item'),
    path('panier/modifier/<int:item_id>/', views.modifier_quantite, name='modifier_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('commande/<int:pk>/paiement/', views.paiement_commande, name='paiement'),
    path('commande/<int:pk>/callback/', views.callback_commande, name='callback'),
    path('commande/<int:pk>/succes/', views.succes_commande, name='succes_commande'),
    path('<slug:slug>/', views.detail_produit, name='detail'),
]
