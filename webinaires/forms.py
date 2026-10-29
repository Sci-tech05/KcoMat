from datetime import datetime

from django import forms
from django.utils import timezone

from .catalogue import HEURE_DEBUT, HEURE_FIN
from .models import Webinaire

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


class WebinaireAdminForm(forms.ModelForm):
    """Admin : une seule date, une heure de début et une heure de fin (au lieu de deux dates complètes)."""
    jour = forms.DateField(label="Date")
    heure_debut = forms.TimeField(label="Heure de début")
    heure_fin = forms.TimeField(label="Heure de fin")

    class Meta:
        model = Webinaire
        exclude = ['date_debut', 'date_fin']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.admin.widgets import AdminDateWidget, AdminTimeWidget
        self.fields['jour'].widget = AdminDateWidget()
        self.fields['heure_debut'].widget = AdminTimeWidget(format='%H:%M')
        self.fields['heure_fin'].widget = AdminTimeWidget(format='%H:%M')
        if self.instance.pk:
            debut = timezone.localtime(self.instance.date_debut)
            self.initial.update(jour=debut.date(), heure_debut=debut.time().replace(second=0, microsecond=0),
                                heure_fin=timezone.localtime(self.instance.date_fin).time().replace(second=0, microsecond=0))
        else:
            self.initial.update(heure_debut=HEURE_DEBUT, heure_fin=HEURE_FIN)

    def clean(self):
        donnees = super().clean()
        jour, debut, fin = donnees.get('jour'), donnees.get('heure_debut'), donnees.get('heure_fin')
        if jour and debut and fin:
            if fin <= debut:
                self.add_error('heure_fin', "L'heure de fin doit être après l'heure de début.")
            else:
                zone = timezone.get_current_timezone()
                nouveau_debut = timezone.make_aware(datetime.combine(jour, debut), zone)
                if self.instance.pk and nouveau_debut != self.instance.date_debut:
                    self.instance.rappel_envoye_le = None   # séance déplacée : le rappel repartira
                # lu par Webinaire.clean() et enregistré avec le reste du formulaire
                self.instance.date_debut = nouveau_debut
                self.instance.date_fin = timezone.make_aware(datetime.combine(jour, fin), zone)
        return donnees
