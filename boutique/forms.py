from django import forms
from .models import Commande


class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = ['prenom', 'nom', 'email', 'telephone', 'adresse_livraison', 'ville', 'notes', 'mode_paiement']
        widgets = {
            'mode_paiement': forms.RadioSelect(attrs={'class': 'mt-0.5 h-4 w-4 flex-shrink-0 accent-blue-600'}),
            'prenom': forms.TextInput(attrs={'placeholder': 'Prénom', 'class': 'form-input'}),
            'nom': forms.TextInput(attrs={'placeholder': 'Nom', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'votre@email.com', 'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+229 XX XX XX XX', 'class': 'form-input'}),
            'adresse_livraison': forms.Textarea(attrs={
                'placeholder': 'Adresse complète de livraison',
                'rows': 2,
                'class': 'form-textarea',
            }),
            'ville': forms.TextInput(attrs={'placeholder': 'Ville', 'class': 'form-input'}),
            'notes': forms.Textarea(attrs={
                'placeholder': 'Instructions de livraison (optionnel)',
                'rows': 2,
                'class': 'form-textarea',
            }),
        }
