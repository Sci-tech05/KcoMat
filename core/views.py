from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import TeamMember, Temoignage, Statistique
from .forms import ContactForm
from formations.models import Formation
from services.models import Service
from boutique.models import Produit


def accueil(request):
    formations_vedette = Formation.objects.filter(actif=True).order_by('-en_vedette', '-created_at')[:6]
    services = Service.objects.filter(actif=True)[:6]
    produits_vedette = Produit.objects.filter(actif=True, en_vedette=True)[:8]
    temoignages = Temoignage.objects.filter(actif=True)[:6]
    statistiques = Statistique.objects.all()[:6]
    ctx = {
        'formations_vedette': formations_vedette,
        'services': services,
        'produits_vedette': produits_vedette,
        'temoignages': temoignages,
        'statistiques': statistiques,
        'title': 'Accueil',
    }
    return render(request, 'core/accueil.html', ctx)


def a_propos(request):
    membres = TeamMember.objects.all()
    ctx = {
        'membres': membres,
        'title': 'À propos de KcoMat',
    }
    return render(request, 'core/a_propos.html', ctx)


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        msg = form.save()
        try:
            send_mail(
                subject=f"[KcoMat] Nouveau message : {msg.sujet}",
                message=f"De : {msg.nom} ({msg.email})\nTél : {msg.telephone}\n\n{msg.message}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.KCOMAT_INFO['email']],
                fail_silently=True,
            )
        except Exception:
            pass
        messages.success(request, "✅ Votre message a été envoyé avec succès ! Nous vous répondrons bientôt.")
        return redirect('core:contact')
    return render(request, 'core/contact.html', {'form': form, 'title': 'Contact'})


def confidentialite(request):
    return render(request, 'core/confidentialite.html', {'title': 'Politique de confidentialité'})
