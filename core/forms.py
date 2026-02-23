from django import forms
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['nom', 'email', 'telephone', 'sujet', 'message']
        widgets = {
            'nom': forms.TextInput(attrs={'placeholder': 'Votre nom complet', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'votre@email.com', 'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+229 XX XX XX XX', 'class': 'form-input'}),
            'sujet': forms.TextInput(attrs={'placeholder': 'Sujet de votre message', 'class': 'form-input'}),
            'message': forms.Textarea(attrs={
                'placeholder': 'Décrivez votre demande en détail...',
                'rows': 5,
                'class': 'form-textarea',
            }),
        }
        labels = {
            'nom': 'Nom complet',
            'email': 'Adresse email',
            'telephone': 'Téléphone',
            'sujet': 'Sujet',
            'message': 'Message',
        }
