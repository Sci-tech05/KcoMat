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


class DemandeAccompagnementForm(DemandeServiceForm):
    """Section 0 de la fiche « Demande d'accompagnement de projets techniques »."""

    class Meta(DemandeServiceForm.Meta):
        fields = ['nom', 'email', 'telephone', 'localite', 'structure', 'intitule_projet', 'description_besoin']
        labels = {
            'nom': 'Nom et prénom(s)',
            'telephone': 'Contact (téléphone)',
            'localite': 'Adresse / Ville',
            'description_besoin': 'Présentez votre projet',
        }
        widgets = {
            **DemandeServiceForm.Meta.widgets,
            'localite': forms.TextInput(attrs={'placeholder': 'Ex. Lokossa, quartier…', 'class': 'form-input'}),
            'structure': forms.TextInput(attrs={'placeholder': 'École, université, entreprise… (optionnel)', 'class': 'form-input'}),
            'intitule_projet': forms.TextInput(attrs={'placeholder': 'Ex. Système d’irrigation automatique', 'class': 'form-input'}),
            'description_besoin': forms.Textarea(attrs={
                'placeholder': 'Le thème, ce que le système doit faire, vos délais, ce que vous avez déjà…',
                'rows': 4,
                'class': 'form-textarea',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['intitule_projet'].required = True
