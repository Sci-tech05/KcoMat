from django import forms
from .models import Inscription


class InscriptionForm(forms.ModelForm):
    class Meta:
        model = Inscription
        fields = ['prenom', 'nom', 'email', 'telephone', 'adresse', 'mode_preference', 'niveau_actuel', 'message']
        widgets = {
            'prenom': forms.TextInput(attrs={'placeholder': 'Votre prenom', 'class': 'form-input'}),
            'nom': forms.TextInput(attrs={'placeholder': 'Votre nom', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'votre@email.com', 'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+229 XX XX XX XX', 'class': 'form-input'}),
            'adresse': forms.TextInput(attrs={'placeholder': 'Votre adresse complete', 'class': 'form-input'}),
            'mode_preference': forms.Select(attrs={'class': 'form-input'}),
            'niveau_actuel': forms.TextInput(attrs={'placeholder': 'Ex: Lyceen, Technicien, Ingenieur...', 'class': 'form-input'}),
            'message': forms.Textarea(attrs={
                'placeholder': 'Questions ou informations supplementaires...',
                'rows': 3,
                'class': 'form-textarea',
            }),
        }
        labels = {
            'prenom': 'Prenom',
            'nom': 'Nom',
            'email': 'Email',
            'telephone': 'Telephone',
            'adresse': 'Adresse',
            'mode_preference': 'Preference',
            'niveau_actuel': 'Niveau actuel / Profession',
            'message': 'Message (optionnel)',
        }
