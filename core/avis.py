"""Avis clients (étoiles + commentaire) sur les composants et les formations."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Avis

AVIS_AFFICHES = 20


def _modeles():
    # import tardif : évite les imports circulaires entre applications
    from boutique.models import Produit
    from formations.models import Formation
    return {'produit': Produit, 'formation': Formation}


def type_de(objet):
    for nom, modele in _modeles().items():
        if isinstance(objet, modele):
            return nom
    raise ValueError(f'Avis non pris en charge pour {type(objet).__name__}')


def achat_verifie(objet, utilisateur):
    """Le client a-t-il payé ce composant / cette formation ?"""
    if not utilisateur.is_authenticated:
        return False
    if type_de(objet) == 'produit':
        from boutique.models import CommandeItem
        return CommandeItem.objects.filter(
            produit=objet, commande__utilisateur=utilisateur,
            commande__statut__in=['payee', 'en_preparation', 'expediee', 'livree'],
        ).exists()
    from formations.models import Inscription
    return Inscription.objects.filter(
        formation=objet, utilisateur=utilisateur, statut__in=['frais_payes', 'complet', 'termine'],
    ).exists()


class AvisForm(forms.ModelForm):
    class Meta:
        model = Avis
        fields = ['note', 'commentaire']
        widgets = {'commentaire': forms.Textarea(attrs={'rows': 4, 'maxlength': 1500})}


def resume(objet, utilisateur):
    """Contexte du bloc « Avis clients » d'une page de détail."""
    ct = ContentType.objects.get_for_model(objet)
    publies = Avis.objects.filter(content_type=ct, object_id=objet.pk, publie=True)
    stats = publies.aggregate(moyenne=Avg('note'), nombre=Count('id'))
    par_note = dict(publies.values_list('note').annotate(n=Count('id')))
    nombre = stats['nombre'] or 0
    repartition = [
        {'note': n, 'nombre': par_note.get(n, 0), 'pourcent': round(100 * par_note.get(n, 0) / nombre) if nombre else 0}
        for n in range(5, 0, -1)
    ]
    mon_avis = None
    if utilisateur.is_authenticated:
        mon_avis = Avis.objects.filter(content_type=ct, object_id=objet.pk, utilisateur=utilisateur).first()
    return {
        'type': type_de(objet),
        'objet': objet,
        'liste': publies.select_related('utilisateur')[:AVIS_AFFICHES],
        'nombre': nombre,
        'moyenne': round(stats['moyenne'], 1) if stats['moyenne'] else None,
        'repartition': repartition,
        'mon_avis': mon_avis,
        'form': AvisForm(instance=mon_avis),
    }


@login_required
@require_POST
def donner_avis(request, type_objet, pk):
    modele = _modeles().get(type_objet)
    if modele is None:
        raise Http404
    objet = get_object_or_404(modele, pk=pk, actif=True)
    ct = ContentType.objects.get_for_model(objet)
    existant = Avis.objects.filter(content_type=ct, object_id=objet.pk, utilisateur=request.user).first()
    form = AvisForm(request.POST, instance=existant)
    if form.is_valid():
        avis = form.save(commit=False)
        avis.content_type, avis.object_id, avis.utilisateur = ct, objet.pk, request.user
        avis.achat_verifie = achat_verifie(objet, request.user)
        avis.save()
        messages.success(request, 'Merci ! Votre avis a été mis à jour.' if existant else 'Merci pour votre avis !')
    else:
        messages.error(request, 'Choisissez une note de 1 à 5 étoiles.')
    page = 'boutique:detail' if type_objet == 'produit' else 'formations:detail'
    return redirect(reverse(page, args=[objet.slug]) + '#avis')
