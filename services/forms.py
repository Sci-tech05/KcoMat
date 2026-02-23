from django import forms
from .models import DemandeService


class DemandeServiceForm(forms.ModelForm):
    class Meta:
        model = DemandeService
        fields = ['nom', 'email', 'telephone', 'localite', 'description_besoin', 'budget_estime']
        widgets = {
            'nom': forms.TextInput(attrs={'placeholder': 'Votre nom complet', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'votre@email.com', 'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+229 XX XX XX XX', 'class': 'form-input'}),
            'localite': forms.TextInput(attrs={'placeholder': 'Votre localité', 'class': 'form-input'}),
            'description_besoin': forms.Textarea(attrs={
                'placeholder': 'Décrivez votre besoin en détail...',
                'rows': 4,
                'class': 'form-textarea',
            }),
            'budget_estime': forms.TextInput(attrs={'placeholder': 'Optionnel', 'class': 'form-input'}),
        }
