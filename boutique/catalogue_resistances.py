"""
Catégorie « Résistances » du catalogue de la boutique.

Liste établie d'après la catégorie Résistances de components.youpilab.com (octobre 2026) :
`prix_source` est le prix affiché là-bas ; le prix de vente KcoMat est majoré de 30 %
(voir `catalogue.prix_majore`). Textes rédigés pour KcoMat à partir des caractéristiques techniques.
"""

PRIX_MIN_RESISTANCE = 50  # aucune résistance vendue moins de 50 FCFA

_PUISSANCES = {'1/4': '1/4 W', '1/2': '1/2 W', '1': '1 W'}
_USAGES = {
    '1/4': "La puissance standard des montages électroniques : LED, transistors, ponts diviseurs, résistances de rappel.",
    '1/2': "Un peu plus robuste que la 1/4 W, pour les circuits qui chauffent davantage ou les alimentations.",
    '1': "Pour les circuits de puissance : alimentations, limitation de courant de charges plus fortes.",
}


def _resistance(valeur, puissance, prix, slug, tolerance='5 %', nom=None, alias=None, detail=''):
    """valeur affichée (ex. « 22 kΩ »), puissance '1/4' | '1/2' | '1'."""
    watts = _PUISSANCES[puissance]
    fiche = {
        'nom': nom or f"Résistance {valeur} {watts}{detail}",
        'prix_source': prix, 'ref': f"{valeur} {watts} {tolerance}", 'slug': slug,
        'courte': f"Résistance {valeur}, {watts}, tolérance {tolerance}, à montage traversant.",
        'texte': f"Résistance à couche de {valeur}. {_USAGES[puissance]} Se soude sur circuit imprimé "
                 "ou se plante directement sur une protoboard.",
        'specs': [f"Valeur : {valeur}", f"Puissance : {watts}", f"Tolérance : ±{tolerance}",
                  "Couche carbone ou métal", "Montage traversant (axial)"],
        'prix_min': PRIX_MIN_RESISTANCE,
    }
    if alias:
        fiche['alias'] = alias
    return fiche


RESISTANCES = [
    {'nom': 'Kit de résistances 1/4 W – 600 pièces', 'prix_source': 5000, 'ref': '600 pièces 1/4 W',
     'slug': 'kit-resistances-600-pieces',
     'courte': "Assortiment de 600 résistances 1/4 W de valeurs standard, rangées dans une boîte à compartiments.",
     'texte': "Toutes les valeurs courantes à portée de main pour le prototypage, la réparation et l'enseignement. "
              "Le kit indispensable de l'atelier électronique.",
     'specs': ["600 résistances", "Puissance : 1/4 W", "Large plage de valeurs, de quelques ohms au mégohm",
               "Boîte de rangement compartimentée", "Montage traversant"]},

    # ── 1/4 W ──
    _resistance('220 Ω', '1/4', 20, 'resistance-220-ohms-1-4w', alias=['resistance-220']),
    _resistance('330 Ω', '1/4', 20, 'resistance-330-ohms-1-4w'),
    _resistance('470 Ω', '1/4', 20, 'resistance-470-ohms-1-4w'),
    _resistance('1 kΩ', '1/4', 20, 'resistance-1k-1-4w'),
    _resistance('3,3 kΩ', '1/4', 20, 'resistance-3-3k-1-4w-5'),
    _resistance('3,3 kΩ', '1/4', 20, 'resistance-3-3k-1-4w-1', tolerance='1 %', detail=' 1 % (précision)'),
    _resistance('10 kΩ', '1/4', 20, 'resistance-10k-1-4w'),
    _resistance('82 kΩ', '1/4', 20, 'resistance-82k-1-4w'),

    # ── 1/2 W ──
    _resistance('10 Ω', '1/2', 20, 'resistance-10-ohms-1-2w'),
    _resistance('100 Ω', '1/2', 20, 'resistance-100-ohms-1-2w'),
    _resistance('100 Ω', '1/2', 20, 'resistance-100-ohms-1-2w-b', detail=' (lot B)'),
    _resistance('220 Ω', '1/2', 20, 'resistance-220-ohms-1-2w'),
    _resistance('560 Ω', '1/2', 20, 'resistance-560-ohms-1-2w'),
    _resistance('1 kΩ', '1/2', 20, 'resistance-1k-1-2w'),
    _resistance('2,2 kΩ', '1/2', 20, 'resistance-2-2k-1-2w'),
    _resistance('4,7 kΩ', '1/2', 20, 'resistance-4-7k-1-2w'),
    _resistance('5,6 kΩ', '1/2', 20, 'resistance-5-6k-1-2w'),
    _resistance('6,8 kΩ', '1/2', 20, 'resistance-6-8k-1-2w'),
    _resistance('10 kΩ', '1/2', 20, 'resistance-10k-1-2w'),
    _resistance('82 kΩ', '1/2', 20, 'resistance-82k-1-2w'),
    _resistance('100 kΩ', '1/2', 20, 'resistance-100k-1-2w'),
    _resistance('470 kΩ', '1/2', 20, 'resistance-470k-1-2w'),
    _resistance('1 MΩ', '1/2', 20, 'resistance-1m-1-2w'),
    _resistance('10 MΩ', '1/2', 20, 'resistance-10m-1-2w'),

    # ── 1 W ──
    _resistance('1 kΩ', '1', 40, 'resistance-1k-1w'),
    _resistance('1,5 kΩ', '1', 40, 'resistance-1-5k-1w'),
    _resistance('2,2 kΩ', '1', 40, 'resistance-2-2k-1w'),
    _resistance('4,7 kΩ', '1', 40, 'resistance-4-7k-1w'),
    _resistance('22 kΩ', '1', 40, 'resistance-22k-1w'),
    _resistance('27 kΩ', '1', 40, 'resistance-27k-1w'),
    _resistance('47 kΩ', '1', 40, 'resistance-47k-1w'),
    _resistance('470 kΩ', '1', 40, 'resistance-470k-1w'),
    _resistance('2,2 MΩ', '1', 40, 'resistance-2-2m-1w'),
]
