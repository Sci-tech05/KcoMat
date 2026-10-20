from django import forms
from .models import Candidature, DOCUMENT_MAX_MB


class MotivationTextarea(forms.Textarea):
    # Le template de candidature choisit le rendu selon widget.input_type.
    input_type = 'textarea'


class CandidatureForm(forms.ModelForm):
    class Meta:
        model = Candidature
        fields = ['formule', 'prenom', 'nom', 'email', 'telephone', 'cv', 'lettre_motivation', 'message']
        widgets = {
            'prenom': forms.TextInput(attrs={'placeholder': 'Prénom', 'class': 'form-input', 'autocomplete': 'given-name'}),
            'nom': forms.TextInput(attrs={'placeholder': 'Nom', 'class': 'form-input', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'votre@email.com', 'class': 'form-input', 'autocomplete': 'email'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+229 XX XX XX XX', 'class': 'form-input',
                                                'autocomplete': 'tel', 'inputmode': 'tel'}),
            'cv': forms.FileInput(attrs={'class': 'form-file', 'accept': '.pdf,.doc,.docx'}),
            'lettre_motivation': forms.FileInput(attrs={'class': 'form-file', 'accept': '.pdf,.doc,.docx'}),
            'message': MotivationTextarea(attrs={'placeholder': 'Présentez-vous en quelques lignes : parcours, compétences, disponibilité…',
                                                 'maxlength': 1500}),
        }
        labels = {
            'cv': f'CV (PDF ou Word, {DOCUMENT_MAX_MB} Mo max.)',
            'lettre_motivation': f'Lettre de motivation (PDF ou Word, {DOCUMENT_MAX_MB} Mo max.)',
            'message': 'Votre motivation (facultatif)',
            'prenom': 'Prénom',
            'telephone': 'Téléphone',
            'email': 'E-mail',
        }

    def __init__(self, *args, offre=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.offre = offre
        formules = offre.formules.all() if offre is not None else None
        if formules:
            field = self.fields['formule']
            field.queryset = formules
            field.required = True
            field.empty_label = None
            field.widget = forms.RadioSelect(choices=field.choices)
            field.label = 'Formule souhaitée'
            field.error_messages['required'] = 'Choisissez une durée de stage.'
        else:
            del self.fields['formule']

    def clean_email(self):
        """Une seule candidature par personne (adresse e-mail) et par offre."""
        email = (self.cleaned_data.get('email') or '').strip()
        if self.offre is not None and email:
            existante = (Candidature.objects.filter(offre=self.offre, email__iexact=email)
                         .order_by('-created_at').first())
            if existante:
                raise forms.ValidationError(
                    f"Vous avez déjà postulé à cette offre le {existante.created_at:%d/%m/%Y} avec cette adresse e-mail. "
                    "Notre équipe étudie votre dossier : inutile de postuler à nouveau.")
        return email
