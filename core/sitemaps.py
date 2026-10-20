from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from boutique.models import Produit
from carrieres.models import Offre
from formations.models import Formation
from projets.models import Projet
from services.models import Service


class PagesSitemap(Sitemap):
    changefreq = 'monthly'

    PRIORITIES = {
        'core:accueil': 1.0,
        'formations:liste': 0.9,
        'boutique:liste': 0.8,
        'services:liste': 0.8,
        'projets:liste': 0.7,
        'carrieres:liste': 0.6,
        'core:a_propos': 0.6,
        'core:contact': 0.5,
        'partenariats:index': 0.4,
        'core:confidentialite': 0.2,
    }

    def items(self):
        return list(self.PRIORITIES)

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self.PRIORITIES[item]


class SlugSitemap(Sitemap):
    """Objets publics accessibles via <namespace>:detail avec un slug."""
    model = None
    url_name = ''
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return self.model.objects.filter(actif=True).order_by('pk')

    def location(self, obj):
        return reverse(self.url_name, args=[obj.slug])


class FormationSitemap(SlugSitemap):
    model = Formation
    url_name = 'formations:detail'
    priority = 0.9

    def lastmod(self, obj):
        return obj.updated_at


class ProduitSitemap(SlugSitemap):
    model = Produit
    url_name = 'boutique:detail'


class ServiceSitemap(SlugSitemap):
    model = Service
    url_name = 'services:detail'


class ProjetSitemap(SlugSitemap):
    model = Projet
    url_name = 'projets:detail'
    priority = 0.6


class OffreSitemap(SlugSitemap):
    model = Offre
    url_name = 'carrieres:detail'
    priority = 0.5
    changefreq = 'daily'


SITEMAPS = {
    'pages': PagesSitemap,
    'formations': FormationSitemap,
    'produits': ProduitSitemap,
    'services': ServiceSitemap,
    'projets': ProjetSitemap,
    'offres': OffreSitemap,
}
