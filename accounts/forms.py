from django import forms
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, UserCreationForm
from django.contrib.auth.models import User

from .models import ProfilUtilisateur


def email_deja_utilise(email, sauf=None):
    """Vrai si un autre compte utilise déjà cette adresse (sans tenir compte des majuscules)."""
    qs = User.objects.filter(email__iexact=email)
    if sauf is not None:
        qs = qs.exclude(pk=sauf.pk)
    return qs.exists()


class InscriptionForm(UserCreationForm):
    """Inscription : l'e-mail est obligatoire (mot de passe oublié, factures, suivi des commandes)."""
    email = forms.EmailField(
        label='Adresse e-mail',
        help_text='Pour vos factures et pour récupérer votre compte si vous oubliez votre mot de passe.',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if email_deja_utilise(email):
            raise forms.ValidationError('Un compte existe déjà avec cette adresse e-mail. Connectez-vous ou utilisez « Mot de passe oublié ».')
        return email


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'email': 'Adresse e-mail',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2'}),
            'email': forms.EmailInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2', 'autocomplete': 'email'}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email and email_deja_utilise(email, sauf=self.instance):
            raise forms.ValidationError('Cette adresse e-mail est déjà utilisée par un autre compte.')
        return email


class ProfilUtilisateurForm(forms.ModelForm):
    class Meta:
        model = ProfilUtilisateur
        fields = ['adresse', 'telephone']
        labels = {
            'adresse': 'Adresse',
            'telephone': 'Numéro',
        }
        widgets = {
            'adresse': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2'}),
            'telephone': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2'}),
        }


class KcomatPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Mot de passe actuel',
        widget=forms.PasswordInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2'}),
    )
    new_password1 = forms.CharField(
        label='Nouveau mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2'}),
    )
    new_password2 = forms.CharField(
        label='Confirmation du mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2'}),
    )


class MotDePasseOublieForm(PasswordResetForm):
    email = forms.EmailField(label='Adresse e-mail', max_length=254)
