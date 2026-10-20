from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.core.mail import send_mail
from django.conf import settings
from .models import TeamMember, Temoignage, Statistique
from .forms import ContactForm
from formations.models import Formation
from services.models import Service
from boutique.models import Produit
from projets.models import Projet


def accueil(request):
    formations_vedette = Formation.objects.filter(actif=True).order_by('-en_vedette', '-created_at')[:6]
    services = Service.objects.filter(actif=True)[:6]
    # composants mis en avant d'abord, puis les plus récents (la section n'est jamais vide)
    produits_vedette = (Produit.objects.filter(actif=True).select_related('categorie')
                        .order_by('-en_vedette', '-created_at')[:10])
    projets_vedette = (Projet.objects.filter(actif=True).select_related('categorie')
                       .order_by('-en_vedette', '-date_realisation', '-created_at')[:10])
    temoignages = Temoignage.objects.filter(actif=True)[:6]
    statistiques = Statistique.objects.all()[:6]
    ctx = {
        'formations_vedette': formations_vedette,
        'services': services,
        'produits_vedette': produits_vedette,
        'projets_vedette': projets_vedette,
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


ROBOTS_DISALLOW = [
    '/accounts/',
    '/boutique/panier/',
    '/boutique/checkout/',
    '/boutique/commande/',
    '/formations/inscription/',
    '/formations/mes-inscriptions/',
]


@require_GET
@cache_control(max_age=60 * 60 * 24, public=True)
def robots_txt(request):
    # L'URL de l'admin est volontairement absente : la citer la rendrait publique.
    site_url = (settings.FEDAPAY_APP_URL or request.build_absolute_uri('/')).rstrip('/')
    lines = ['User-agent: *', *[f'Disallow: {path}' for path in ROBOTS_DISALLOW], '',
             f'Sitemap: {site_url}/sitemap.xml', '']
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
