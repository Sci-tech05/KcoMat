import logging

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CandidatureForm
from .models import Offre
from .notifications import accuser_reception, notifier_equipe

logger = logging.getLogger(__name__)


def _offres_publiees():
    return Offre.objects.filter(actif=True).prefetch_related('formules')


def liste_offres(request):
    type_filtre = request.GET.get('type', '')
    domaine_filtre = request.GET.get('domaine', '')
    today = timezone.localdate()

    offres = _offres_publiees()
    if type_filtre:
        offres = offres.filter(type_offre=type_filtre)
    if domaine_filtre:
        offres = offres.filter(domaine=domaine_filtre)
    # Ouvertes d'abord (à la une en tête), puis clôturées
    ouvertes = [o for o in offres if not o.est_cloturee]
    cloturees = [o for o in offres if o.est_cloturee]

    base = Offre.objects.filter(actif=True).filter(Q(date_limite__isnull=True) | Q(date_limite__gte=today))
    compte_types = dict(base.values_list('type_offre').annotate(n=Count('id')))
    compte_domaines = dict((base.filter(type_offre=type_filtre) if type_filtre else base)
                           .values_list('domaine').annotate(n=Count('id')))
    domaines = [(cle, label, compte_domaines[cle]) for cle, label in Offre.DOMAINE_CHOICES if compte_domaines.get(cle)]

    ctx = {
        'offres': ouvertes + cloturees,
        'nb_ouvertes': len(ouvertes),
        'type_filtre': type_filtre,
        'domaine_filtre': domaine_filtre,
        'types': [(cle, label, compte_types.get(cle, 0)) for cle, label in Offre.TYPE_CHOICES],
        'total_ouvertes': sum(compte_types.values()),
        'domaines': domaines,
        'title': 'Carrières & Stages',
    }
    return render(request, 'carrieres/liste.html', ctx)


def _envoyer_emails_candidature(candidature):
    """Alerte l'équipe puis accuse réception ; un échec d'e-mail ne bloque jamais la candidature."""
    for envoi in (notifier_equipe, accuser_reception):
        try:
            envoi(candidature)
        except Exception:
            logger.exception("E-mail « %s » impossible pour la candidature #%s", envoi.__name__, candidature.pk)


def detail_offre(request, slug):
    offre = get_object_or_404(_offres_publiees(), slug=slug)
    if request.method == 'POST' and offre.est_cloturee:
        messages.error(request, "Les candidatures pour cette offre sont closes.")
        return redirect('carrieres:detail', slug=offre.slug)

    form = CandidatureForm(request.POST or None, request.FILES or None, offre=offre)
    if request.method == 'POST' and form.is_valid():
        candidature = form.save(commit=False)
        candidature.offre = offre
        candidature.save()
        transaction.on_commit(lambda: _envoyer_emails_candidature(candidature))
        messages.success(request, "Votre candidature a bien été envoyée ! Un e-mail de confirmation vous a été adressé.")
        return redirect('carrieres:detail', slug=offre.slug)

    similaires = (_offres_publiees().exclude(pk=offre.pk)
                  .filter(Q(domaine=offre.domaine) | Q(type_offre=offre.type_offre))
                  .order_by('-mise_en_avant', '-created_at')[:3])
    ctx = {
        'offre': offre,
        'form': form,
        'similaires': similaires,
        'formules': list(offre.formules.all()),
        'durees': ' ou '.join(f.duree for f in offre.formules.all()),
        'title': offre.titre,
    }
    return render(request, 'carrieres/detail.html', ctx)
