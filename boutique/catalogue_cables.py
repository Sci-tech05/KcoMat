"""
Catégorie « Câbles & Connecteurs » du catalogue de la boutique.

Liste établie d'après la catégorie Câbles de components.youpilab.com (octobre 2026) :
`prix_source` est le prix affiché là-bas ; le prix de vente KcoMat est majoré de 30 %
(voir `catalogue.prix_majore`), sauf « prix_fixe » (jumpers alignés sur le prix KcoMat de 50 FCFA l'unité).
Non repris : « Chargeur Raspberry Pi3 », affiché à 0 FCFA (prix inconnu).
"""

PRIX_JUMPER_UNITE = 50  # prix KcoMat d'un jumper à l'unité


def _fiche(nom, prix, ref, slug, courte, texte, specs, **extra):
    return {'nom': nom, 'prix_source': prix, 'ref': ref, 'slug': slug, 'courte': courte, 'texte': texte, 'specs': specs, **extra}


def _jumper(type_, longueur, prix, slug, alias=None, prix_fixe=None):
    noms = {'M-M': 'mâle-mâle', 'F-F': 'femelle-femelle', 'M-F': 'mâle-femelle'}
    extra = {}
    if alias:
        extra['alias'] = alias
    if prix_fixe:
        extra['prix_fixe'] = prix_fixe
    return _fiche(
        f"Jumper {noms[type_]} {longueur} (l'unité)", prix, f"Dupont {type_} {longueur}", slug,
        f"Fil de connexion Dupont {noms[type_]} de {longueur}, vendu à l'unité.",
        "Pour relier modules, cartes et protoboard sans soudure.",
        [f"Connecteurs {noms[type_]} type Dupont", f"Longueur : {longueur}", "Couleur selon disponibilité", "Prix à l'unité"],
        **extra)


def _lot_jumpers(type_, longueur, prix, slug, prix_fixe=None):
    noms = {'M-M': 'mâle-mâle', 'F-F': 'femelle-femelle', 'M-F': 'mâle-femelle'}
    extra = {'prix_fixe': prix_fixe} if prix_fixe else {}
    return _fiche(
        f"Lot de 40 jumpers {noms[type_]} {longueur}", prix, f"40 × Dupont {type_} {longueur}", slug,
        f"Nappe de 40 fils Dupont {noms[type_]} de {longueur}, détachables, de couleurs différentes.",
        "Les fils se séparent un par un selon vos besoins : le lot idéal pour équiper un atelier ou une classe.",
        [f"40 fils {noms[type_]}", f"Longueur : {longueur}", "Fils détachables, multicolores", "Compatible protoboard et cartes Arduino"],
        **extra)


def _usb(nom, prix, slug, connecteur, longueur, usage):
    return _fiche(nom, prix, f"USB A → {connecteur}", slug,
                  f"Câble USB A vers {connecteur} ({longueur}) pour {usage}.",
                  "Transmet les données et l'alimentation : programmation des cartes depuis l'ordinateur et recharge.",
                  [f"USB A → {connecteur}", f"Longueur : {longueur}", "Données + alimentation"])


CABLES = [
    # ── Jumpers ──
    _jumper('M-M', '20 cm', 35, 'jumper-male-male-20cm', alias=['jumpers-m-m']),
    _jumper('F-F', '22 cm', 35, 'jumper-femelle-femelle-22cm', alias=['jumpers-f-f']),
    _jumper('M-F', '22 cm', 35, 'jumper-male-femelle-22cm', alias=['jumpers-m-f']),
    _jumper('M-M', '30 cm', 40, 'jumper-male-male-30cm', prix_fixe=PRIX_JUMPER_UNITE),
    _jumper('F-F', '30 cm', 40, 'jumper-femelle-femelle-30cm', prix_fixe=PRIX_JUMPER_UNITE),
    _jumper('M-F', '30 cm', 40, 'jumper-male-femelle-30cm', prix_fixe=PRIX_JUMPER_UNITE),
    _lot_jumpers('M-M', '20 cm', 1400, 'lot-40-jumpers-male-male-20cm'),
    _lot_jumpers('F-F', '20 cm', 1400, 'lot-40-jumpers-femelle-femelle-20cm'),
    _lot_jumpers('M-F', '20 cm', 1400, 'lot-40-jumpers-male-femelle-20cm'),
    # 30 cm : 1600 + 30 % dépasserait 50 FCFA l'unité → plafonné à 40 × 50
    _lot_jumpers('M-M', '30 cm', 1600, 'lot-40-jumpers-male-male-30cm', prix_fixe=40 * PRIX_JUMPER_UNITE),
    _lot_jumpers('F-F', '30 cm', 1600, 'lot-40-jumpers-femelle-femelle-30cm', prix_fixe=40 * PRIX_JUMPER_UNITE),
    _lot_jumpers('M-F', '30 cm', 1600, 'lot-40-jumpers-male-femelle-30cm', prix_fixe=40 * PRIX_JUMPER_UNITE),

    # ── Câbles Grove ──
    _fiche('Câble Grove 2 broches 30 cm', 185, 'Grove 2 pins', 'cable-grove-2-broches',
           "Câble Grove 2 broches de 30 cm pour brancher les modules Grove sans soudure.",
           "Connecteurs détrompés : impossible de se tromper de sens.", ["2 broches", "Longueur : 30 cm", "Connecteurs Grove"]),
    _fiche('Câble Grove 3 broches 30 cm', 245, 'Grove 3 pins', 'cable-grove-3-broches',
           "Câble Grove 3 broches de 30 cm pour brancher les modules Grove sans soudure.",
           "Connecteurs détrompés : impossible de se tromper de sens.", ["3 broches", "Longueur : 30 cm", "Connecteurs Grove"]),
    _fiche('Câble Grove 5 broches 30 cm', 345, 'Grove 5 pins', 'cable-grove-5-broches',
           "Câble Grove 5 broches de 30 cm pour brancher les modules Grove sans soudure.",
           "Connecteurs détrompés : impossible de se tromper de sens.", ["5 broches", "Longueur : 30 cm", "Connecteurs Grove"]),
    _fiche('Câble Grove 50 cm', 350, 'Grove', 'cable-grove-50cm',
           "Câble Grove 4 broches de 50 cm, pour éloigner un module Grove de la carte.",
           "Alimentation et signaux (I2C, UART, numérique ou analogique) dans un seul câble détrompé.",
           ["Longueur : 50 cm", "Connecteurs Grove"]),

    # ── Câbles USB, HDMI, réseau ──
    _usb('Câble USB A vers USB-C 50 cm', 1200, 'cable-usb-a-usb-c-50cm', 'USB-C', '50 cm',
         "les cartes et appareils récents (ESP32-C3, Raspberry Pi 4, téléphones)"),
    _usb('Câble USB A vers micro USB 1 m', 500, 'cable-usb-a-micro-b-1m', 'micro USB', '1 m',
         "les cartes ESP32 / ESP8266 et les téléphones"),
    _usb('Câble USB A vers mini USB', 580, 'cable-usb-a-mini-b', 'mini USB', 'longueur standard',
         "l'Arduino Nano et les anciens appareils"),
    _usb('Câble USB Arduino Uno 60 cm (bleu)', 504, 'cable-usb-arduino-uno-60cm', 'USB B', '60 cm', "l'Arduino Uno et Mega"),
    _usb('Câble USB Arduino Uno 3 m (noir)', 566, 'cable-usb-arduino-uno-3m', 'USB B', '3 m',
         "l'Arduino Uno et Mega, les imprimantes et scanners"),
    _fiche('Câble HDMI', 1500, 'HDMI', 'cable-hdmi',
           "Câble HDMI pour relier ordinateur, Raspberry Pi, écran, téléviseur ou vidéoprojecteur.",
           "Transmet l'image et le son en haute définition.", ["HDMI ↔ HDMI", "Image et son"]),
    _fiche('Câble micro HDMI vers HDMI 1,5 m', 3500, 'micro HDMI → HDMI', 'cable-micro-hdmi-hdmi',
           "Câble micro HDMI vers HDMI de 1,5 m, indispensable pour brancher un Raspberry Pi 4 sur un écran.",
           "Transfert de l'image et du son vers un téléviseur ou un moniteur HDMI.", ["Micro HDMI → HDMI", "Longueur : 1,5 m"]),
    _fiche('Câble réseau Ethernet', 300, 'RJ45', 'cable-reseau-ethernet',
           "Câble réseau RJ45 pour relier un Raspberry Pi, un routeur ou un module Ethernet.",
           "Connexion filaire fiable au réseau local et à Internet.", ["Connecteurs RJ45"]),

    # ── Convertisseurs série ──
    _fiche('Module RS485 ↔ TTL', 1000, 'RS485', 'module-rs485-ttl-compact',
           "Petit convertisseur TTL ↔ RS485 compatible 3,3 V et 5 V, branchable à chaud.",
           "Pour relier un microcontrôleur à un bus RS485 (Modbus, capteurs industriels).",
           ["TTL ↔ RS485", "Compatible 3,3 V et 5 V", "Température : -40 à 85 °C", "Dimensions : 42 × 15 mm"]),
    _fiche('Module RS485 ↔ TTL isolé 2 Mb/s', 3500, 'RS485 isolé', 'module-rs485-ttl-isole',
           "Convertisseur TTL ↔ RS485 à isolation électrique, jusqu'à 2 Mb/s, pour les environnements industriels.",
           "L'isolation protège la carte contre les parasites, les surtensions et les problèmes de masse sur les longues lignes.",
           ["Isolation électrique complète", "Jusqu'à 2 Mb/s", "Sens de transmission automatique", "Compatible 3,3 V et 5 V",
            "Protection TVS"]),
    _fiche('Convertisseur USB ↔ UART FTDI (FT232)', 1210, 'FT232RQ', 'convertisseur-usb-uart-ftdi',
           "Adaptateur USB ↔ série TTL à puce FTDI FT232, pour programmer Arduino Pro Mini, ESP et modules série.",
           "La puce FTDI est reconnue par tous les systèmes et très stable.",
           ["Puce FTDI FT232RQ", "USB → série TTL", "Dimensions : 52 × 15 mm"]),
    _fiche('Câble USB ↔ série TTL 1,8 m', 1850, 'PL2303HX', 'cable-usb-serie-ttl',
           "Câble USB vers série TTL de 1,8 m avec fils séparés, pour se brancher directement sur un port série.",
           "Pour programmer et déboguer cartes et modules, ou dialoguer avec un Raspberry Pi par sa console série.",
           ["USB → série TTL", "Longueur : 1,8 m", "Fils séparés (TX, RX, GND, VCC)"]),

    # ── Alimentation ──
    _fiche('Câble d’alimentation 12V/24V', 260, '12 / 24 V DC', 'cable-alimentation-12v-24v',
           "Câble d'alimentation continue rouge / noir pour relier batterie ou bloc secteur à un appareil.",
           "Pour les montages 12 V et 24 V : rubans LED, caméras, modules et kits solaires.",
           ["12 V / 24 V DC", "Fil rouge (+) et noir (−)", "Conducteurs cuivre, gaine PVC"]),
    _fiche('Connecteur pile 9V avec jack', 275, '9V → jack 5,5 mm', 'connecteur-pile-9v-jack',
           "Coupleur de pile 9 V avec fiche jack : alimente directement un Arduino par sa prise.",
           "La pile alimente la carte par son entrée jack (7 à 12 V conseillés) : idéal pour un projet autonome.",
           ["Clip pile 9 V", "Fiche jack 5,5 / 2,1 mm"]),
    _fiche('Connecteur pile 9V à fils', 190, '9V', 'connecteur-pile-9v-fils',
           "Coupleur de pile 9 V à fils nus, pour protoboard ou soudure.",
           "Alimente vos montages sur pile 9 V, à souder ou à planter sur protoboard.",
           ["Clip pile 9 V", "Fils rouge (+) et noir (−)"]),
    _fiche('Fil de cuivre 24 AWG noir (4 conducteurs)', 500, '24 AWG', 'fil-cuivre-24awg-noir',
           "Câble souple 4 conducteurs 24 AWG en cuivre, pour signaux, capteurs et petites alimentations.",
           "Pour déporter un capteur, un écran ou des LED loin de la carte.", ["4 conducteurs", "24 AWG", "Cuivre", "Gaine noire souple"]),

    # ── Connecteurs ──
    _fiche('Connecteur mâle 2 broches (pas 2,54 mm)', 25, '2,54 mm', 'connecteur-male-2-broches',
           "Barrette mâle 2 broches au pas standard de 2,54 mm, pour circuits imprimés et protoboard.",
           "Pour les connexions d'alimentation et de signaux sur cartes et modules.",
           ["2 broches", "Pas : 2,54 mm", "Montage sur circuit imprimé"], prix_min=50),
    _fiche('Connecteur JST-XH', 480, 'JST-XH 2,54 mm', 'connecteur-jst-xh',
           "Connecteur JST-XH au pas de 2,54 mm, détrompé : équilibreurs de batteries, imprimantes 3D, modules.",
           "Connexion stable qui ne peut pas être branchée à l'envers.",
           ["Pas : 2,54 mm", "Jusqu'à 3 A, 250 V", "Détrompé"]),
    _fiche('Connecteur JST-PH 2.0 femelle', 200, 'JST-PH 2,0 mm', 'connecteur-jst-ph-20',
           "Connecteur JST-PH 2 broches pour batteries lithium et petits modules (TP4056, drones).",
           "Compact et détrompé : le standard des petites batteries Li-Po.",
           ["Pas : 2,0 mm", "2 broches (rouge / noir)", "Femelle"]),
    _fiche('Connecteur banane mâle', 240, 'Banane 4 mm', 'connecteur-banane-male',
           "Fiche banane mâle à vis pour fabriquer vos cordons de mesure et d'alimentation.",
           "Se raccorde aux multimètres et alimentations de laboratoire.",
           ["Fiche mâle", "Serrage par vis (fil jusqu'à 1,5 mm²)", "Plusieurs couleurs"]),
    _fiche('Connecteur banane femelle', 185, 'Banane 4 mm', 'connecteur-banane-femelle',
           "Douille banane femelle pour façades d'alimentations et boîtiers de mesure.",
           "Accueille les cordons à fiche banane des appareils de mesure.", ["Douille femelle", "Plusieurs couleurs"]),
    _fiche('Cordons à pinces crocodile (couleurs mélangées)', 200, '50 cm', 'cordons-pinces-crocodile',
           "Cordons de test à pinces crocodile aux deux bouts, pour relier rapidement composants et appareils.",
           "Idéal pour les essais, l'enseignement et les mesures sans soudure.",
           ["Pinces crocodile aux deux extrémités", "Longueur : 50 cm", "Couleurs différentes"]),
]
