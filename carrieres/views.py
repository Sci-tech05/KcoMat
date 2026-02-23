from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Offre, Candidature
from .forms import CandidatureForm


def liste_offres(request):
    type_filtre = request.GET.get('type', '')
    offres = Offre.objects.filter(actif=True)
    if type_filtre:
        offres = offres.filter(type_offre=type_filtre)
    ctx = {
        'offres': offres,
        'type_filtre': type_filtre,
        'title': 'Carrières & Stages',
    }
    return render(request, 'carrieres/liste.html', ctx)


def detail_offre(request, slug):
    offre = get_object_or_404(Offre, slug=slug, actif=True)
    form = CandidatureForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        candidature = form.save(commit=False)
        candidature.offre = offre
        candidature.save()
        messages.success(request, "✅ Votre candidature a bien été envoyée ! Nous vous contacterons si votre profil correspond.")
        return redirect('carrieres:detail', slug=offre.slug)
    ctx = {'offre': offre, 'form': form, 'title': offre.titre}
    return render(request, 'carrieres/detail.html', ctx)
