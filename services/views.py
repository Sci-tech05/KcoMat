from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Service, DemandeService
from .forms import DemandeServiceForm
from core.notifications_admin import notifier_admin


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
        notifier_admin(
            type_evenement='service', sujet=f"Demande de devis : {service.titre} — {demande.nom}",
            titre='Nouvelle demande de service',
            intro=f"{demande.nom} demande un devis pour « {service.titre} ».",
            details=[('Service', service.titre), ('Nom', demande.nom), ('E-mail', demande.email),
                     ('Téléphone', demande.telephone), ('Localité', demande.localite), ('Budget estimé', demande.budget_estime)],
            message=demande.description_besoin, objet=demande, repondre_a=demande.email, request=request,
        )
        messages.success(request, "✅ Votre demande a été envoyée ! Nous vous contacterons rapidement.")
        return redirect('services:detail', slug=service.slug)
    ctx = {'service': service, 'form': form, 'title': service.titre, 'autres_services': autres_services}
    return render(request, 'services/detail.html', ctx)
