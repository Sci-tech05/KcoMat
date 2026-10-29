from django import forms

CHAMP = ('w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 '
         'focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20')


class InscriptionWebinaireForm(forms.Form):
    """Nom et prénom tels qu'ils figureront sur l'attestation."""
    prenom = forms.CharField(label="Prénom", max_length=100,
                             widget=forms.TextInput(attrs={'class': CHAMP, 'autocomplete': 'given-name'}))
    nom = forms.CharField(label="Nom", max_length=100,
                          widget=forms.TextInput(attrs={'class': CHAMP, 'autocomplete': 'family-name'}))

    def clean_prenom(self):
        return ' '.join(self.cleaned_data['prenom'].split()).title()

    def clean_nom(self):
        return ' '.join(self.cleaned_data['nom'].split()).upper()
