"""Paiement en deux tranches (formations, boutique) : la moitié maintenant, le solde ensuite.

Les frais fixes de 2 000 FCFA (inscription, consultation) ne sont jamais fractionnés.
"""

TOTAL = 'total'
DEUX_TRANCHES = 'deux_tranches'
CHOIX = [
    (TOTAL, 'Paiement total'),
    (DEUX_TRANCHES, 'En 2 tranches (50 % maintenant, 50 % ensuite)'),
]


def premiere_tranche(montant):
    """Moitié du montant, arrondie au franc supérieur (le solde ne dépasse jamais la 1re tranche)."""
    return (int(montant) + 1) // 2


def solde(montant):
    return int(montant) - premiere_tranche(montant)


def fcfa(montant):
    return f"{int(montant):,} FCFA".replace(',', ' ')
