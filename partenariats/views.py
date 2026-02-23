from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Partenaire, DemandePartenariat
from .forms import DemandePartenariatForm


def partenariats(request):
    partenaires = Partenaire.objects.filter(actif=True)
    form = DemandePartenariatForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "✅ Votre demande de partenariat a été transmise. Nous vous recontacterons très prochainement !")
        return redirect('partenariats:index')
    ctx = {
        'partenaires': partenaires,
        'form': form,
        'title': 'Partenariats & Entreprises',
    }
    return render(request, 'partenariats/index.html', ctx)
