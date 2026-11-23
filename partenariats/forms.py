from django import forms
from .models import DemandePartenariat


class DemandePartenariatForm(forms.ModelForm):
    class Meta:
        model = DemandePartenariat
        fields = [
            'nom_organisation', 'email', 'telephone',
            'site_web', 'type_partenariat_souhaite', 'logo',
        ]
        widgets = {
            'nom_organisation': forms.TextInput(attrs={'placeholder': 'Nom de votre organisation', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@organisation.com', 'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+229 XX XX XX XX', 'class': 'form-input'}),
            'site_web': forms.URLInput(attrs={'placeholder': 'https://...', 'class': 'form-input'}),
            'type_partenariat_souhaite': forms.TextInput(attrs={
                'placeholder': 'Ex: Co-formation, Sponsoring, Équipement...',
                'class': 'form-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['nom_organisation', 'email', 'telephone']:
            self.fields[f].required = True
        self.fields['site_web'].required = False
        self.fields['type_partenariat_souhaite'].required = False
        self.fields['logo'].required = False

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo and logo.size > LOGO_TAILLE_MAX:
            raise forms.ValidationError("Logo trop lourd : 5 Mo au maximum.")
        return logo


LOGO_TAILLE_MAX = 5 * 1024 * 1024
