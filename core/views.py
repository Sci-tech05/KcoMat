from datetime import date

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.conf import settings
from .models import TeamMember, Temoignage, Statistique
from .forms import ContactForm
from .notifications_admin import notifier_admin
from formations.models import Formation
from services.models import Service
from boutique.models import Produit
from projets.models import Projet
from webinaires.views import avec_inscrits, contexte_cartes
from webinaires.models import Webinaire


def accueil(request):
    formations_vedette = Formation.objects.filter(actif=True).order_by('ordre', 'titre')[:10]
    services = Service.objects.filter(actif=True)[:6]
    # composants mis en avant d'abord, puis les plus récents (la section n'est jamais vide)
    produits_vedette = (Produit.objects.filter(actif=True).select_related('categorie')
                        .order_by('-en_vedette', '-created_at')[:10])
    projets_vedette = (Projet.objects.filter(actif=True).select_related('categorie')
                       .order_by('-en_vedette', '-date_realisation', '-created_at')[:10])
    temoignages = Temoignage.objects.filter(actif=True)[:6]
    statistiques = Statistique.objects.all()[:6]
    # webinaires à venir (ou en direct) : en tête de page, juste sous le héros
    webinaires_accueil = contexte_cartes(request, list(avec_inscrits(Webinaire.objects.a_venir())[:3]))
    ctx = {
        'webinaires_accueil': webinaires_accueil,
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
        notifier_admin(
            type_evenement='contact', sujet=f"Nouveau message : {msg.sujet}",
            titre='Nouveau message de contact',
            intro=f"{msg.nom} vous a écrit depuis la page Contact du site.",
            details=[('Nom', msg.nom), ('E-mail', msg.email), ('Téléphone', msg.telephone), ('Sujet', msg.sujet)],
            message=msg.message, objet=msg, repondre_a=msg.email, request=request,
        )
        messages.success(request, "✅ Votre message a été envoyé avec succès ! Nous vous répondrons bientôt.")
        return redirect('core:contact')
    return render(request, 'core/contact.html', {'form': form, 'title': 'Contact'})


# Pages légales : date à changer à chaque modification du texte
MISE_A_JOUR_LEGALE = date(2026, 11, 23)

SOMMAIRE_CONFIDENTIALITE = [
    ('responsable', 'Responsable du traitement'),
    ('donnees', 'Données collectées'),
    ('finalites', 'Finalités et bases légales'),
    ('destinataires', 'Destinataires et prestataires'),
    ('transferts', 'Hébergement et transferts'),
    ('conservation', 'Durées de conservation'),
    ('cookies', 'Cookies et stockage local'),
    ('notifications', 'Notifications push'),
    ('securite', 'Sécurité'),
    ('droits', 'Vos droits'),
    ('modifications', 'Modifications'),
]

SOMMAIRE_MENTIONS = [
    ('editeur', 'Éditeur du site'),
    ('publication', 'Directeur de la publication'),
    ('hebergement', 'Hébergement'),
    ('propriete', 'Propriété intellectuelle'),
    ('responsabilite', 'Responsabilité'),
    ('commandes', 'Commandes et paiements'),
    ('attestations', 'Attestations'),
    ('liens', 'Liens et contenus externes'),
    ('donnees', 'Données personnelles'),
    ('droit', 'Droit applicable'),
]


def confidentialite(request):
    return render(request, 'core/confidentialite.html', {
        'title': 'Politique de confidentialité',
        'sommaire': SOMMAIRE_CONFIDENTIALITE,
        'mise_a_jour': MISE_A_JOUR_LEGALE,
    })


def mentions_legales(request):
    return render(request, 'core/mentions_legales.html', {
        'title': 'Mentions légales',
        'sommaire': SOMMAIRE_MENTIONS,
        'mise_a_jour': MISE_A_JOUR_LEGALE,
        'directeur_publication': settings.KCOMAT_INFO.get('directeur_publication', ''),
    })


ROBOTS_DISALLOW = [
    '/accounts/',
    '/boutique/panier/',
    '/boutique/checkout/',
    '/boutique/commande/',
    '/formations/inscription/',
    '/formations/mes-inscriptions/',
    '/webinaires/attestation/',
]


@require_GET
@cache_control(max_age=60 * 60 * 24, public=True)
def robots_txt(request):
    # L'URL de l'admin est volontairement absente : la citer la rendrait publique.
    site_url = (settings.FEDAPAY_APP_URL or request.build_absolute_uri('/')).rstrip('/')
    lines = ['User-agent: *', *[f'Disallow: {path}' for path in ROBOTS_DISALLOW], '',
             f'Sitemap: {site_url}/sitemap.xml', '']
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
