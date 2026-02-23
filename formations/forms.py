from django import forms
from .models import Inscription


class InscriptionForm(forms.ModelForm):
    class Meta:
        model = Inscription
        fields = ['prenom', 'nom', 'email', 'telephone', 'niveau_actuel', 'message']
        widgets = {
            'prenom': forms.TextInput(attrs={'placeholder': 'Votre prénom', 'class': 'form-input'}),
            'nom': forms.TextInput(attrs={'placeholder': 'Votre nom', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'votre@email.com', 'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+229 XX XX XX XX', 'class': 'form-input'}),
            'niveau_actuel': forms.TextInput(attrs={'placeholder': 'Ex: Lycéen, Technicien, Ingénieur...', 'class': 'form-input'}),
            'message': forms.Textarea(attrs={
                'placeholder': 'Questions ou informations supplémentaires...',
                'rows': 3,
                'class': 'form-textarea',
            }),
        }
        labels = {
            'prenom': 'Prénom',
            'nom': 'Nom',
            'email': 'Email',
            'telephone': 'Téléphone',
            'niveau_actuel': 'Niveau actuel / Profession',
            'message': 'Message (optionnel)',
        }
