from django.shortcuts import render, get_object_or_404
from .models import Projet, CategorieProjet


def liste_projets(request):
    categories = CategorieProjet.objects.all()
    cat_slug = request.GET.get('categorie', '')
    projets = Projet.objects.filter(actif=True)
    if cat_slug:
        projets = projets.filter(categorie__slug=cat_slug)
    ctx = {
        'projets': projets,
        'categories': categories,
        'cat_active': cat_slug,
        'title': 'Nos Projets Réalisés',
    }
    return render(request, 'projets/liste.html', ctx)


def detail_projet(request, slug):
    projet = get_object_or_404(Projet, slug=slug, actif=True)
    ctx = {
        'projet': projet,
        'images': projet.images.all(),
        'videos': projet.videos.all(),
        'title': projet.titre,
    }
    return render(request, 'projets/detail.html', ctx)
