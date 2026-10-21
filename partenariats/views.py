from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Partenaire, DemandePartenariat
from .forms import DemandePartenariatForm
from core.notifications_admin import notifier_admin


def partenariats(request):
    partenaires = Partenaire.objects.filter(actif=True)
    form = DemandePartenariatForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        demande = form.save()
        notifier_admin(
            type_evenement='partenariat', sujet=f"Demande de partenariat : {demande.nom_organisation}",
            titre='Nouvelle demande de partenariat',
            intro=f"{demande.nom_organisation} souhaite devenir partenaire de KcoMat.",
            details=[('Organisation', demande.nom_organisation), ("Type d'organisation", demande.type_organisation),
                     ('Contact', demande.nom_contact), ('E-mail', demande.email), ('Téléphone', demande.telephone),
                     ('Site web', demande.site_web), ('Partenariat souhaité', demande.type_partenariat_souhaite)],
            message=demande.description_projet, objet=demande, repondre_a=demande.email, request=request,
        )
        messages.success(request, "✅ Votre demande de partenariat a été transmise. Nous vous recontacterons très prochainement !")
        return redirect('partenariats:index')
    ctx = {
        'partenaires': partenaires,
        'form': form,
        'title': 'Partenariats & Entreprises',
    }
    return render(request, 'partenariats/index.html', ctx)
