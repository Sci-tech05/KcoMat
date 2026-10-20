from django import template
from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

from boutique.models import Commande
from carrieres.models import Candidature
from core.models import ContactMessage
from formations.models import Inscription
from notifications.models import AbonnementPush
from partenariats.models import DemandePartenariat
from services.models import DemandeService

register = template.Library()

COMMANDES_PAYEES = ['payee', 'en_preparation', 'expediee', 'livree']


@register.simple_tag
def admin_dashboard():
    """Indicateurs du tableau de bord admin (quelques requêtes agrégées)."""
    now = timezone.localtime()
    debut_mois = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    inscriptions = Inscription.objects.aggregate(
        total=Count('id'),
        ce_mois=Count('id', filter=Q(created_at__gte=debut_mois)),
        en_attente=Count('id', filter=Q(statut='en_attente')),
        completes=Count('id', filter=Q(statut='complet')),
        # anciennes inscriptions : statut renseigné sans date de paiement
        frais_payes=Count('id', filter=Q(frais_payes_le__isnull=False) | Q(statut__in=['frais_payes', 'complet'])),
        en_ligne=Count('id', filter=Q(mode_preference='en_ligne')),
    )
    revenus_formations = (
        inscriptions['frais_payes'] * settings.KCOMAT_INFO['frais_inscription']
        + (Inscription.objects.filter(Q(formation_payee_le__isnull=False) | Q(statut='complet'))
           .aggregate(s=Sum('formation__prix'))['s'] or 0)
    )

    commandes = Commande.objects.aggregate(
        total=Count('id'),
        payees=Count('id', filter=Q(statut__in=COMMANDES_PAYEES)),
        en_attente=Count('id', filter=Q(statut='en_attente')),
        revenus=Sum('montant_total', filter=Q(statut__in=COMMANDES_PAYEES)),
    )

    a_traiter = {
        'messages': ContactMessage.objects.filter(lu=False).count(),
        'services': DemandeService.objects.filter(traite=False).count(),
        'candidatures': Candidature.objects.filter(statut__in=['nouvelle', 'en_revue']).count(),
        'partenariats': DemandePartenariat.objects.filter(traite=False).count(),
    }

    return {
        'now': now,
        'inscriptions': inscriptions,
        'revenus_formations': int(revenus_formations),
        'commandes': commandes,
        'revenus_boutique': int(commandes['revenus'] or 0),
        'revenus_total': int(revenus_formations) + int(commandes['revenus'] or 0),
        'a_traiter': a_traiter,
        'a_traiter_total': sum(a_traiter.values()),
        'abonnes_push': AbonnementPush.objects.filter(actif=True).count(),
        'dernieres_inscriptions': Inscription.objects.select_related('formation').order_by('-created_at')[:6],
    }
