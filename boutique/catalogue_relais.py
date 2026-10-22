"""
Catégorie « Relais » du catalogue de la boutique.

Liste établie d'après la catégorie Relais de components.youpilab.com (octobre 2026) :
`prix_source` est le prix affiché là-bas ; le prix de vente KcoMat est majoré de 30 %
(voir `catalogue.prix_majore`). Textes rédigés pour KcoMat à partir des caractéristiques techniques.
"""


def _module(canaux, tension, prix, slug, nom=None, alias=None):
    pluriel = 's' if canaux > 1 else ''
    fiche = {
        'nom': nom or f"Module relais {canaux} canal{'aux' if canaux > 1 else ''} {tension}",
        'prix_source': prix, 'ref': f"{canaux} × relais {tension}", 'slug': slug,
        'courte': f"Module de {canaux} relais {tension} pour commander {'des appareils' if canaux > 1 else 'un appareil'} "
                  f"220 V (lampes, prises, pompes) depuis un Arduino, un ESP32 ou un automate.",
        'texte': f"Chaque relais commute une charge jusqu'à 10 A. Les contacts sont sur borniers à vis et "
                 f"une LED indique l'état de chaque canal. Bobine{pluriel} alimentée{pluriel} en {tension}.",
        'specs': [f"{canaux} relais, bobine {tension}", "Contacts jusqu'à 10 A sous 250 V AC (ou 30 V DC)",
                  "Contacts NO / NF / commun sur borniers à vis", "Commande : 15 à 20 mA par relais", "LED témoin par canal"],
    }
    if alias:
        fiche['alias'] = alias
    return fiche


def _ssr(modele, prix, commande, charge, courant, slug=None, nom=None):
    return {
        'nom': nom or f"Relais statique {modele} {courant} A",
        'prix_source': prix, 'ref': modele, 'slug': slug or f"relais-statique-{modele.lower()}",
        'courte': f"Relais statique (SSR) {courant} A sans pièce mobile : commutation silencieuse et sans usure. "
                  f"Commande {commande}, charge {charge}.",
        'texte': "Le relais statique commute électroniquement : pas de bruit, pas d'étincelle, une durée de vie très longue. "
                 "Idéal pour les résistances chauffantes, fours, couveuses et régulations de température. "
                 "Au-delà de quelques ampères, montez-le sur un dissipateur thermique.",
        'specs': [f"Courant de charge : jusqu'à {courant} A", f"Tension de commande : {commande}", f"Charge : {charge}",
                  "Voyant de commande intégré", "À monter sur dissipateur pour les forts courants"],
    }


_DC_AC = ('3 à 32 V DC', '24 à 380 V AC')
_DC_DC = ('3 à 32 V DC', 'courant continu')
_AC_AC = ('80 à 250 V AC', '24 à 380 V AC')

RELAIS = [
    # ── Relais seuls ──
    {'nom': 'Relais 5V simple', 'prix_source': 300, 'ref': 'SRD-05VDC', 'slug': 'relais-5v-simple', 'alias': ['relais-5v', 'relay-5v'],
     'courte': "Relais 5 V à souder, 10 A.", 'texte': "Relais électromécanique classique à bobine 5 V.",
     'specs': ["Bobine 5 V DC", "Contacts 10 A sous 250 V AC"]},
    {'nom': 'Relais 3V (5 broches)', 'prix_source': 290, 'ref': 'SRD-03VDC',
     'slug': 'relais-3v-5-broches',
     'courte': "Relais à bobine 3 V à souder, 10 A : se commande facilement depuis une carte 3,3 V.",
     'texte': "Pour commuter une charge 220 V ou continue depuis un montage alimenté en 3 V. "
              "À commander via un transistor, avec une diode de roue libre.",
     'specs': ["Bobine 3 V DC", "Contacts 10 A sous 250 V AC ou 30 V DC", "Un contact inverseur, 5 broches",
               "Dimensions : 18,6 × 15,1 × 15,5 mm"]},
    {'nom': 'Relais 12V (5 broches)', 'prix_source': 290, 'ref': 'SRD-12VDC',
     'slug': 'relais-12v-5-broches',
     'courte': "Relais à bobine 12 V à souder, 10 A, pour montages alimentés en 12 V (batterie, solaire).",
     'texte': "Relais électromécanique classique pour circuits 12 V : automobile, kits solaires, automatismes.",
     'specs': ["Bobine 12 V DC (400 Ω)", "Contacts 10 A sous 250 V AC ou 30 V DC", "Un contact inverseur, 5 broches"]},
    {'nom': 'Relais 5V grande puissance', 'prix_source': 720, 'ref': '',
     'slug': 'relais-5v-grande-puissance',
     'courte': "Relais de puissance à bobine 5 V pour les charges plus fortes qu'un relais standard 10 A.",
     'texte': "Pour commander climatiseurs, pompes, chauffe-eau ou moteurs depuis une carte électronique, via un transistor.",
     'specs': ["Bobine 5 V DC", "Contacts de forte puissance", "À souder"]},
    {'nom': 'Relais de maintien magnétique HFE10-2 12-HT-L2', 'prix_source': 3110, 'ref': 'HFE10-2/12-HT-L2',
     'slug': 'relais-bistable-hfe10-2-12-ht-l2',
     'courte': "Relais bistable : une impulsion suffit pour l'ouvrir ou le fermer, il garde ensuite sa position sans consommer.",
     'texte': "Un aimant permanent maintient le contact après l'impulsion de commande. Idéal pour les compteurs d'énergie, "
              "les coupures programmées et les systèmes sur batterie.",
     'specs': ["Relais à maintien magnétique (bistable)", "Bobine 12 V DC", "Commande par impulsion", "Aucune consommation au repos"]},
    {'nom': 'Relais de maintien magnétique HFE10-2 12-H1T-L2', 'prix_source': 4585, 'ref': 'HFE10-2/12-H1T-L2',
     'slug': 'relais-bistable-hfe10-2-12-h1t-l2',
     'courte': "Relais bistable 12 V à maintien magnétique, variante H1T : garde sa position sans consommer.",
     'texte': "Une impulsion de commande ouvre ou ferme le contact, qui reste ensuite dans sa position. "
              "Pour compteurs d'énergie à prépaiement et commandes à faible consommation.",
     'specs': ["Relais à maintien magnétique (bistable)", "Bobine 12 V DC", "Commande par impulsion", "Aucune consommation au repos"]},

    # ── Modules 5 V ──
    _module(1, '5V', 475, 'module-relais-5v-1-canal', nom='Module relais 5V 1 canal'),
    {**_module(1, '5V', 450, 'module-relais-5v-1-canal-low', nom='Module relais 5V 1 canal (commande niveau bas)'),
     'courte': "Module 1 relais 5 V activé par un niveau bas (0 V) : commande une charge 220 V depuis une carte."},
    {**_module(1, '5V', 800, 'module-relais-5v-1-canal-optocoupleur', nom='Module relais 5V 1 canal avec optocoupleur'),
     'texte': "Un optocoupleur isole la carte de commande du circuit de puissance. Déclenchement au niveau haut ou bas "
              "selon le cavalier. Contacts jusqu'à 10 A sur borniers à vis."},
    _module(2, '5V', 865, 'module-relais-5v-2-canaux', nom='Module relais 5V 2 canaux', alias=['module-relais-2-canaux']),
    _module(4, '5V', 1575, 'module-relais-5v-4-canaux', nom='Module relais 5V 4 canaux'),
    _module(8, '5V', 3150, 'module-relais-5v-8-canaux', nom='Module relais 5V 8 canaux'),
    _module(16, '5V', 8250, 'module-relais-5v-16-canaux', nom='Module relais 5V 16 canaux'),

    # ── Modules 12 V ──
    _module(1, '12V', 500, 'module-relais-12v-1-canal', nom='Module relais 12V 1 canal'),
    _module(2, '12V', 965, 'module-relais-12v-2-canaux', nom='Module relais 12V 2 canaux'),
    _module(4, '12V', 1775, 'module-relais-12v-4-canaux', nom='Module relais 12V 4 canaux'),
    _module(8, '12V', 3350, 'module-relais-12v-8-canaux', nom='Module relais 12V 8 canaux'),
    _module(16, '12V', 8450, 'module-relais-12v-16-canaux', nom='Module relais 12V 16 canaux'),

    # ── Modules grande puissance (30 A) ──
    {'nom': 'Module relais 5V 30A 1 canal avec optocoupleur', 'prix_source': 2000, 'ref': '30 A',
     'slug': 'module-relais-5v-30a-optocoupleur',
     'courte': "Module relais 30 A isolé par optocoupleur, pour les fortes charges : climatiseur, chauffe-eau, pompe.",
     'texte': "Le relais 30 A commute de gros appareils depuis un Arduino ou un ESP32. Déclenchement au niveau haut ou bas "
              "par cavalier ; LED d'alimentation et d'état.",
     'specs': ["Bobine 5 V", "Charge max : 30 A sous 250 V AC ou 30 V DC", "Isolation par optocoupleur",
               "Déclenchement haut / bas au choix", "Dimensions : 50 × 33 × 24 mm"]},
    {'nom': 'Module relais grande puissance 1 canal', 'prix_source': 2160, 'ref': '30 A',
     'slug': 'module-relais-grande-puissance-1-canal',
     'courte': "Module 1 relais 30 A commandé en 5 V, isolé par optocoupleur, sur borniers à vis.",
     'texte': "Pour commander une charge importante en domotique ou en automatisme, en toute sécurité pour la carte de commande.",
     'specs': ["Commande 5 V", "Jusqu'à 30 A sous 250 V AC ou 30 V DC", "Optocoupleur intégré", "Borniers à vis"]},
    {'nom': 'Module relais grande puissance 2 canaux', 'prix_source': 3970, 'ref': '2 × 30 A',
     'slug': 'module-relais-grande-puissance-2-canaux',
     'courte': "Module 2 relais 30 A commandés en 5 V, entrées isolées par optocoupleur.",
     'texte': "Commande indépendante de deux fortes charges : pompe et chauffe-eau, deux climatiseurs, etc.",
     'specs': ["2 relais, commande 5 V", "Jusqu'à 30 A sous 250 V AC ou 30 V DC", "Entrées opto-isolées", "Borniers à vis"]},
    {'nom': 'Module relais grande puissance 4 canaux', 'prix_source': 7850, 'ref': '4 × 30 A',
     'slug': 'module-relais-grande-puissance-4-canaux',
     'courte': "Module 4 relais 30 A commandés en 5 V, entrées isolées par optocoupleur.",
     'texte': "Pour piloter quatre fortes charges depuis une seule carte : tableaux domotiques, automatismes, ateliers.",
     'specs': ["4 relais, commande 5 V", "Jusqu'à 30 A sous 250 V AC ou 30 V DC", "Entrées opto-isolées", "Borniers à vis"]},
    {'nom': 'Module relais industriel 16 canaux 24V rail DIN', 'prix_source': 24000, 'ref': 'TK73 / T73',
     'slug': 'module-relais-16-canaux-24v-rail-din',
     'courte': "Module 16 relais 24 V DC sur rail DIN, pour automates programmables et armoires électriques.",
     'texte': "Interface entre un automate (PLC) ou un microcontrôleur et les charges de puissance, avec une LED d'état par canal.",
     'specs': ["16 relais, alimentation 24 V DC", "Contacts inverseurs (NO / NF / COM)", "Montage sur rail DIN",
               "LED d'état par canal"]},

    # ── Relais statiques ──
    _ssr('SSR-40DA', 2755, *_DC_AC, 40),
    _ssr('SSR-60DA', 4060, *_DC_AC, 60),
    _ssr('SSR-100DA', 5795, *_DC_AC, 100),
    _ssr('SSR-100DA', 5545, *_DC_AC, 100, slug='relais-statique-dc-ac-100a',
         nom='Relais statique DC-AC 100 A (3-32 V DC / 24-380 V AC)'),
    _ssr('SSR-40DD', 4345, *_DC_DC, 40),
    _ssr('SSR-60DD', 5075, *_DC_DC, 60),
    _ssr('SSR-100DD', 7100, *_DC_DC, 100),
    _ssr('SSR-40AA', 3050, *_AC_AC, 40),
    _ssr('SSR-60AA', 4055, *_AC_AC, 60),
    _ssr('SSR-100AA', 5795, *_AC_AC, 100),
    {'nom': 'Module relais statique 5V 1 canal', 'prix_source': 1180, 'ref': 'SSR 5 V',
     'slug': 'module-relais-statique-5v-1-canal',
     'courte': "Module relais statique 5 V : commute silencieusement une petite charge 220 V depuis une carte.",
     'texte': "Sans contact mécanique, il ne s'use pas et ne fait aucun bruit : éclairage, petits chauffages, ventilateurs.",
     'specs': ["Commande 5 V DC", "Charge en courant alternatif (petites puissances)", "Silencieux, sans usure", "Borniers à vis"]},
    {'nom': 'Module relais statique 5V 2 canaux', 'prix_source': 2400, 'ref': '2 × SSR 5 V',
     'slug': 'module-relais-statique-5v-2-canaux',
     'courte': "Module de 2 relais statiques 5 V pour commuter deux petites charges 220 V sans bruit.",
     'texte': "Deux canaux indépendants sans contact mécanique : éclairage, ventilateurs, petits chauffages.",
     'specs': ["Commande 5 V DC", "2 canaux", "Charge en courant alternatif (petites puissances)", "Silencieux, sans usure"]},

    # ── Domotique ──
    {'nom': 'Commutateur intelligent 4 canaux Wi-Fi / RF 433 MHz', 'prix_source': 13550, 'ref': 'TYWB 4CH RF',
     'slug': 'commutateur-intelligent-4-canaux-wifi-rf',
     'courte': "4 relais pilotables depuis le téléphone (Wi-Fi), en Bluetooth ou par télécommande 433 MHz.",
     'texte': "Rendez intelligents vos éclairages, portail ou pompe : commande à distance, minuteries et scénarios "
              "depuis une application mobile.",
     'specs': ["4 canaux", "Alimentation 7 à 32 V AC/DC ou USB 5 V", "10 A par canal, 16 A au total",
               "Wi-Fi 2,4 GHz + Bluetooth", "Radiocommande 433 MHz"]},
]
