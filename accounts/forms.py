from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User

from .models import ProfilUtilisateur


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-gray-300 px-3 py-2'}),
        }


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
