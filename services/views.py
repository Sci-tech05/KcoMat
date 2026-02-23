from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Service, DemandeService
from .forms import DemandeServiceForm


def liste_services(request):
    services = Service.objects.filter(actif=True)
    ctx = {'services': services, 'title': 'Nos Services'}
    return render(request, 'services/liste.html', ctx)


def detail_service(request, slug):
    service = get_object_or_404(Service, slug=slug, actif=True)
    autres_services = Service.objects.filter(actif=True).exclude(slug=slug).order_by('ordre')[:4]
    form = DemandeServiceForm(request.POST or None, initial={'service': service})
    if request.method == 'POST' and form.is_valid():
        demande = form.save(commit=False)
        demande.service = service
        demande.save()
        messages.success(request, "✅ Votre demande a été envoyée ! Nous vous contacterons rapidement.")
        return redirect('services:detail', slug=service.slug)
    ctx = {'service': service, 'form': form, 'title': service.titre, 'autres_services': autres_services}
    return render(request, 'services/detail.html', ctx)
