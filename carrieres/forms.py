from django import forms
from .models import Candidature


class CandidatureForm(forms.ModelForm):
    class Meta:
        model = Candidature
        fields = ['prenom', 'nom', 'email', 'telephone', 'cv', 'lettre_motivation']
        widgets = {
            'prenom': forms.TextInput(attrs={'placeholder': 'Prénom', 'class': 'form-input'}),
            'nom': forms.TextInput(attrs={'placeholder': 'Nom', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'votre@email.com', 'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+229 XX XX XX XX', 'class': 'form-input'}),
            'cv': forms.FileInput(attrs={'class': 'form-file', 'accept': '.pdf,.doc,.docx'}),
            'lettre_motivation': forms.FileInput(attrs={'class': 'form-file', 'accept': '.pdf,.doc,.docx'}),
        }
        labels = {
            'cv': 'CV (PDF, Word)',
            'lettre_motivation': 'Lettre de motivation (PDF, Word)',
        }
