import logging
from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .attestation import reponse_pdf
from .forms import InscriptionWebinaireForm
from .models import ParticipationWebinaire, Webinaire
from .rappels import confirmer_inscription, invitation_ics

logger = logging.getLogger(__name__)


def avec_inscrits(queryset):
    return queryset.annotate(n_inscrits=Count('participations'))


def participations_par_webinaire(user, webinaires):
    """{webinaire_id: participation} pour l'utilisateur connecté (affichage des boutons sur les cartes)."""
    if not user.is_authenticated:
        return {}
    ids = [w.pk for w in webinaires]
    return {p.webinaire_id: p for p in ParticipationWebinaire.objects.filter(utilisateur=user, webinaire_id__in=ids)}


def contexte_cartes(request, webinaires):
    """Prépare des cartes : chaque webinaire reçoit .etat (statut) et .ma_participation."""
    maintenant = timezone.now()
    mes = participations_par_webinaire(request.user, webinaires)
    for webinaire in webinaires:
        webinaire.etat = webinaire.statut(maintenant)
        webinaire.ma_participation = mes.get(webinaire.pk)
    return webinaires


def _webinaire_visible(request, slug):
    qs = Webinaire.objects.all() if request.user.is_staff else Webinaire.objects.publies()
    return get_object_or_404(avec_inscrits(qs), slug=slug)


def _formulaire_initial(user):
    return InscriptionWebinaireForm(initial={'prenom': user.first_name, 'nom': user.last_name})


def liste(request):
    maintenant = timezone.now()
    a_venir = contexte_cartes(request, list(avec_inscrits(Webinaire.objects.a_venir(maintenant))))
    passes = contexte_cartes(request, list(avec_inscrits(Webinaire.objects.passes(maintenant))[:6]))
    return render(request, 'webinaires/liste.html', {
        'a_la_une': a_venir[0] if a_venir else None,
        'suivants': a_venir[1:],
        'passes': passes,
        'title': 'Webinaires',
    })


def detail(request, slug):
    webinaire = _webinaire_visible(request, slug)
    contexte_cartes(request, [webinaire])
    form = None
    if request.user.is_authenticated and not webinaire.ma_participation:
        form = _formulaire_initial(request.user)
    autres = contexte_cartes(request, list(avec_inscrits(Webinaire.objects.a_venir().exclude(pk=webinaire.pk))[:3]))
    return render(request, 'webinaires/detail.html', {
        'webinaire': webinaire,
        'participation': webinaire.ma_participation,
        'form': form,
        'autres': autres,
        'title': webinaire.titre,
    })


def _creer_participation(webinaire, user, prenom, nom):
    try:
        participation, cree = ParticipationWebinaire.objects.get_or_create(
            webinaire=webinaire, utilisateur=user,
            defaults={'prenom': prenom, 'nom': nom, 'email': user.email},
        )
    except IntegrityError:      # double clic : l'inscription existe déjà
        return ParticipationWebinaire.objects.get(webinaire=webinaire, utilisateur=user), False
    champs = [c for c, v in (('first_name', prenom), ('last_name', nom)) if not getattr(user, c) and v]
    if champs:
        user.first_name = user.first_name or prenom
        user.last_name = user.last_name or nom
        user.save(update_fields=champs)
    return participation, cree


@login_required
@require_POST
def inscrire(request, slug):
    webinaire = _webinaire_visible(request, slug)
    page = reverse('webinaires:detail', args=[slug])
    if webinaire.statut() == 'termine':
        messages.warning(request, "Ce webinaire est terminé : les inscriptions sont closes.")
        return redirect(page)
    if ParticipationWebinaire.objects.filter(webinaire=webinaire, utilisateur=request.user).exists():
        messages.info(request, "Votre place est déjà réservée pour ce webinaire.")
        return redirect(page)
    if webinaire.est_complet():
        messages.error(request, "Ce webinaire est complet. Abonnez-vous aux notifications pour être prévenu(e) des prochains.")
        return redirect(page)
    form = InscriptionWebinaireForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Indiquez votre prénom et votre nom : ils figureront sur votre attestation.")
        return redirect(f"{page}#reserver")
    participation, cree = _creer_participation(webinaire, request.user, form.cleaned_data['prenom'], form.cleaned_data['nom'])
    if cree and participation.email:
        try:
            confirmer_inscription(participation)
        except Exception:
            logger.exception("Confirmation d'inscription au webinaire #%s non envoyée", webinaire.pk)
    if webinaire.salle_ouverte():
        return redirect('webinaires:salle', slug=slug)
    messages.success(request, "C'est noté : votre place est réservée. Un rappel vous sera envoyé 20 minutes avant le début.")
    return redirect(page)


def _jitsi(webinaire, user, participation):
    url = webinaire.get_salle_url()
    parsed = urlparse(url)
    nom = (participation.nom_complet if participation else '') or user.get_full_name() or user.username
    return {
        'meet_url': url,
        'jitsi_domain': parsed.netloc,
        'jitsi_external_api_url': f"{parsed.scheme or 'https'}://{parsed.netloc}/external_api.js" if parsed.netloc else '',
        'jitsi_room_name': parsed.path.lstrip('/'),
        'jitsi_display_name': f"{nom} (KcoMat)" if user.is_staff else nom,
        'jitsi_user_email': user.email or '',
    }


@login_required
def salle(request, slug):
    webinaire = _webinaire_visible(request, slug)
    page = reverse('webinaires:detail', args=[slug])
    animateur = request.user.is_staff
    if not animateur and not webinaire.salle_ouverte():
        if webinaire.statut() == 'termine':
            messages.info(request, "La séance est terminée. Si vous y avez participé, téléchargez votre attestation ci-dessous.")
        else:
            debut = timezone.localtime(webinaire.ouverture_salle)
            messages.info(request, f"La salle ouvrira le {debut:%d/%m/%Y} à {debut:%H:%M}, 10 minutes avant le début.")
        return redirect(page)

    participation = ParticipationWebinaire.objects.filter(webinaire=webinaire, utilisateur=request.user).first()
    if participation is None and not animateur:
        if webinaire.est_complet():
            messages.error(request, "Ce webinaire est complet.")
            return redirect(page)
        if not (request.user.first_name and request.user.last_name):
            messages.info(request, "Indiquez votre prénom et votre nom (pour votre attestation), puis entrez dans la salle.")
            return redirect(f"{page}#reserver")
        participation, _ = _creer_participation(webinaire, request.user, request.user.first_name, request.user.last_name)
    if participation and participation.rejoint_le is None:
        ParticipationWebinaire.objects.filter(pk=participation.pk, rejoint_le__isnull=True).update(rejoint_le=timezone.now())

    payload = _jitsi(webinaire, request.user, participation)
    if not payload['jitsi_domain']:
        messages.error(request, "La salle de visioconférence n'est pas configurée. Contactez-nous.")
        return redirect(page)
    return render(request, 'webinaires/salle.html', {
        'webinaire': webinaire,
        'etat': webinaire.statut(),
        'animateur': animateur,
        'title': f"En direct — {webinaire.titre}",
        **payload,
    })


def agenda(request, slug):
    webinaire = _webinaire_visible(request, slug)
    response = HttpResponse(invitation_ics(webinaire), content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="webinaire-kcomat-{webinaire.slug}.ics"'
    return response


@login_required
def attestation(request, slug):
    webinaire = _webinaire_visible(request, slug)
    page = reverse('webinaires:detail', args=[slug])
    participation = ParticipationWebinaire.objects.filter(webinaire=webinaire, utilisateur=request.user).select_related('webinaire').first()
    if participation is None:
        messages.error(request, "Aucune inscription à ce webinaire n'est associée à votre compte.")
        return redirect(page)
    if webinaire.statut() != 'termine':
        messages.info(request, "Votre attestation sera disponible dès la fin de la séance.")
        return redirect(page)
    if not participation.a_participe:
        messages.warning(request, "L'attestation est réservée aux personnes ayant rejoint la séance en direct. "
                                  "Contactez-nous si vous pensez qu'il s'agit d'une erreur.")
        return redirect(page)
    return reponse_pdf(participation)


def verifier_attestation(request, code):
    participation = (ParticipationWebinaire.objects.select_related('webinaire')
                     .filter(code_verification=code).first())
    valide = bool(participation and participation.attestation_disponible())
    return render(request, 'webinaires/verifier.html', {
        'participation': participation if valide else None,
        'code': code,
        'title': "Vérification d'attestation",
    }, status=200 if valide else 404)
