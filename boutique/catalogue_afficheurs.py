"""
Catégorie « LED & Afficheurs » du catalogue de la boutique.

Liste établie d'après la catégorie LEDs, LCDs & Afficheurs de components.youpilab.com (octobre 2026) :
`prix_source` est le prix affiché là-bas ; le prix de vente KcoMat est majoré de 30 %
(voir `catalogue.prix_majore`). Textes rédigés pour KcoMat à partir des caractéristiques techniques.
"""

PRIX_MIN_LED = 50  # aucune LED vendue moins de 50 FCFA

_SPECS_LED_3MM = ["Diamètre : 3 mm", "Tension directe : environ 2 à 2,4 V (3 V pour bleu et blanc)",
                  "Courant conseillé : 16 à 18 mA (20 mA max)", "À utiliser avec une résistance en série"]
_SPECS_LED_10MM = ["Diamètre : 10 mm", "Courant : environ 10 à 20 mA", "Forte luminosité", "À utiliser avec une résistance en série"]


def _led(couleur, prix, slug, taille='3 mm', detail='', specs=None, alias=None, nom=None):
    fiche = {
        'nom': nom or f"LED {couleur} {taille}{detail}",
        'prix_source': prix, 'ref': f"LED {taille}", 'slug': slug,
        'courte': f"LED {couleur} de {taille} pour voyants, signalisation et montages électroniques.",
        'texte': f"Diode électroluminescente {couleur} de {taille}. Branchez-la toujours avec une résistance en série "
                 "(ex. 220 Ω sur 5 V) pour limiter le courant.",
        'specs': specs or _SPECS_LED_3MM,
        'prix_min': PRIX_MIN_LED,
    }
    if alias:
        fiche['alias'] = alias
    return fiche


AFFICHEURS = [
    # ── LED simples ──
    _led('rouge', 21, 'led-rouge-visible', nom='LED rouge', alias=['led-rouge']),
    _led('verte', 21, 'led-verte-visible', nom='LED verte', alias=['led-verte']),
    _led('bleue', 21, 'led-bleu', nom='LED bleue', alias=['led-bleue']),
    _led('jaune', 21, 'led-jaune', nom='LED jaune'),
    _led('orange', 21, 'led-orange', nom='LED orange'),
    _led('violette', 20, 'led-violette-transparente', detail=' transparente'),
    _led('verte', 20, 'led-verte-transparente', detail=' transparente'),
    _led('bleue', 20, 'led-bleue-transparente', detail=' transparente'),
    _led('rouge', 20, 'led-rouge-3mm-transparente', detail=' transparente (tête ronde)'),
    _led('blanche', 20, 'led-blanche-3mm-transparente', detail=' transparente (tête ronde)'),
    _led('orange', 19.6, 'led-orange-3mm-transparente', detail=' transparente (tête ronde)'),
    _led('jaune', 20, 'led-jaune-3mm-lot-de-4', detail=' transparente (lot de 4)'),
    _led('rouge', 25, 'led-rouge-10mm', taille='10 mm', specs=_SPECS_LED_10MM),
    _led('verte', 25, 'led-verte-10mm', taille='10 mm', specs=_SPECS_LED_10MM),
    _led('jaune', 25, 'led-jaune-10mm', taille='10 mm', specs=_SPECS_LED_10MM),
    _led('rouge', 55, 'led-rouge-10mm-transparente', taille='10 mm', detail=' transparente', specs=_SPECS_LED_10MM),
    _led('verte', 55, 'led-verte-10mm-transparente', taille='10 mm', detail=' transparente', specs=_SPECS_LED_10MM),
    _led('orange', 55, 'led-orange-10mm-transparente', taille='10 mm', detail=' transparente', specs=_SPECS_LED_10MM),
    _led('blanche', 55, 'led-blanche-10mm-transparente', taille='10 mm', detail=' transparente', specs=_SPECS_LED_10MM),
    _led('jaune', 55, 'led-jaune-10mm-transparente', taille='10 mm', detail=' transparente', specs=_SPECS_LED_10MM),
    {'nom': 'LED RGB cathode commune', 'prix_source': 132, 'ref': 'RGB 4 broches',
     'slug': 'led-rgb-cathode-commune',
     'courte': "Trois LED (rouge, verte, bleue) dans un seul boîtier : mélangez-les pour obtenir presque toutes les couleurs.",
     'texte': "En réglant la luminosité de chaque couleur en PWM, on obtient toutes les teintes. "
              "Cathode commune : la broche la plus longue se relie au GND.",
     'specs': ["Rouge + vert + bleu", "Cathode commune, 4 broches", "Courant max : 20 mA par couleur",
               "Une résistance par couleur"]},
    {'nom': 'Anneau de 24 LED RGB WS2812', 'prix_source': 1500, 'ref': 'WS2812 5050',
     'slug': 'anneau-24-led-rgb-ws2812',
     'courte': "Anneau de 24 LED RGB adressables WS2812 : chaque LED se commande individuellement avec un seul fil.",
     'texte': "Créez des animations lumineuses, une horloge, un indicateur circulaire ou une lampe d'ambiance. "
              "Les anneaux peuvent s'enchaîner.",
     'specs': ["24 LED RGB WS2812 (5050)", "Pilotes intégrés, commande sur 1 fil", "Alimentation 5 V DC",
               "Diamètre extérieur : environ 6,5 cm", "Compatible bibliothèques NeoPixel / FastLED"]},
    {'nom': 'Module de LED de feux tricolores', 'prix_source': 360, 'ref': '',
     'slug': 'module-led-feux-tricolores',
     'courte': "Mini feu de circulation rouge / orange / vert prêt à brancher, pour l'apprentissage et les maquettes.",
     'texte': "Les trois LED ont déjà leurs résistances : il suffit de relier chaque couleur à une sortie de l'Arduino. "
              "Idéal pour le premier projet de programmation.",
     'specs': ["LED rouge, orange et verte", "Résistances intégrées", "Alimentation 5 V", "4 broches (R, J, V, GND)"]},

    # ── Matrices et afficheurs 7 segments ──
    {'nom': 'Matrice LED 8x8 rouge', 'prix_source': 850, 'ref': '1088AS',
     'slug': 'matrice-led-8x8-rouge',
     'courte': "Matrice de 64 LED rouges (8 × 8) à cathode commune pour afficher lettres, chiffres et symboles.",
     'texte': "À piloter avec un MAX7219 ou en multiplexage depuis un microcontrôleur : textes défilants, jeux, animations.",
     'specs': ["64 LED rouges (8 × 8)", "Cathode commune", "Dimensions : 32 × 32 mm", "Tension directe : 2,1 à 2,5 V"]},
    {'nom': 'Module matrice LED RGB 8x8', 'prix_source': 1900, 'ref': 'RGB 8x8 SPI',
     'slug': 'module-matrice-led-rgb-8x8',
     'courte': "Matrice 8 × 8 de LED RGB assemblée, commandée en SPI et chaînable dans les deux directions.",
     'texte': "Affichez des images et animations en couleur. Plusieurs modules peuvent s'assembler pour former un grand panneau.",
     'specs': ["64 LED RGB", "Interface SPI", "Alimentation 5 V (300 mA max)", "Chaînable", "Dimensions : 60 × 60 mm"]},
    {'nom': 'Afficheur 7 segments 1 chiffre rouge', 'prix_source': 288, 'ref': '0,56" anode commune',
     'slug': 'afficheur-7-segments-1-chiffre',
     'courte': "Afficheur 7 segments rouge d'un chiffre (14,2 mm), anode commune.",
     'texte': "Pour afficher un chiffre : compteur, dé électronique, indicateur d'étage. Chaque segment se commande via une résistance.",
     'specs': ["1 chiffre, hauteur 14,2 mm", "Anode commune", "Montage traversant"]},
    {'nom': 'Afficheur 7 segments 2 chiffres', 'prix_source': 350, 'ref': 'Anode commune',
     'slug': 'afficheur-7-segments-2-chiffres',
     'courte': "Afficheur 7 segments de 2 chiffres à anode commune, pour compteurs et minuteries.",
     'texte': "Deux chiffres multiplexés pour afficher de 00 à 99 : score, compte à rebours, température.",
     'specs': ["2 chiffres", "Anode commune", "Montage traversant"]},
    {'nom': 'Afficheur 7 segments 4 chiffres', 'prix_source': 700, 'ref': '',
     'slug': 'afficheur-7-segments-4-chiffres',
     'courte': "Afficheur 7 segments 4 chiffres multiplexé, pour horloges, compteurs et appareils de mesure.",
     'texte': "Composant brut à piloter en multiplexage depuis un microcontrôleur ou avec un driver dédié.",
     'specs': ["4 chiffres", "Afficheur multiplexé", "Montage traversant"]},
    {'nom': 'Module afficheur horloge 4 chiffres TM1637', 'prix_source': 715, 'ref': 'TM1637',
     'slug': 'afficheur-horloge-4-chiffres-tm1637',
     'courte': "Afficheur 4 chiffres avec deux-points et puce TM1637 : seulement 2 fils pour afficher l'heure.",
     'texte': "Le module se commande en 2 fils (CLK et DIO) avec la bibliothèque TM1637 : horloges, minuteurs, chronomètres.",
     'specs': ["4 chiffres 7 segments avec deux-points", "Puce TM1637", "Alimentation 3,3 à 5 V", "Interface 2 fils"]},

    # ── Écrans OLED et TFT ──
    {'nom': 'Écran OLED 0,49 pouce', 'prix_source': 2395, 'ref': 'SSD1306 64x32',
     'slug': 'ecran-oled-049',
     'courte': "Mini écran OLED 64 × 32 pixels en I2C, pour objets portables et très petits montages.",
     'texte': "Monté sur une carte de 15 × 16 mm, il affiche quelques mots ou icônes avec un excellent contraste et une très faible consommation.",
     'specs': ["Diagonale : 0,49 pouce", "Résolution : 64 × 32", "Pilote SSD1306", "Interface I2C", "Alimentation 3,3 à 5 V"]},
    {'nom': 'Écran OLED 0,91 pouce', 'prix_source': 2450, 'ref': 'SSD1306 128x32',
     'slug': 'ecran-oled-091',
     'courte': "Écran OLED allongé 128 × 32 pixels en I2C : jusqu'à 3 lignes de texte, très lisible.",
     'texte': "L'OLED n'a pas besoin de rétroéclairage : contraste élevé, faible consommation, format fin. "
              "Parfait pour afficher une mesure ou un état.",
     'specs': ["Diagonale : 0,91 pouce", "Résolution : 128 × 32", "Pilote SSD1306", "Interface I2C", "Dimensions : 12 × 38 mm"]},
    {'nom': 'Écran OLED 1,3 pouce', 'prix_source': 3600, 'ref': 'SH1106 128x64',
     'slug': 'ecran-oled-13',
     'courte': "Écran OLED blanc 1,3 pouce 128 × 64 pixels en I2C, plus grand et plus lisible que le 0,96 pouce.",
     'texte': "Pour afficher textes, graphiques et menus avec un fort contraste. Utilisable avec les bibliothèques U8g2 / U8glib.",
     'specs': ["Diagonale : 1,3 pouce", "Résolution : 128 × 64", "Pilote SH1106", "Interface I2C (4 broches)", "Pixels blancs"]},
    {'nom': 'Écran OLED 1,3 pouce vertical', 'prix_source': 4100, 'ref': 'OLED 64x128',
     'slug': 'ecran-oled-13-vertical',
     'courte': "Écran OLED 1,3 pouce en orientation verticale (64 × 128), pour montres et objets portables.",
     'texte': "Son format vertical convient aux montres connectées, bracelets et petits instruments de mesure.",
     'specs': ["Diagonale : 1,3 pouce", "Résolution : 64 × 128 (vertical)", "Interface I2C"]},
    {'nom': 'Shield écran tactile TFT 2,4 pouces', 'prix_source': 10499, 'ref': 'TFT 2,4" 240x320',
     'slug': 'shield-ecran-tactile-tft-24',
     'courte': "Écran couleur tactile 2,4 pouces 240 × 320 qui s'enfiche directement sur un Arduino Uno.",
     'texte': "Affichez images, graphiques et boutons tactiles en couleur : interfaces de commande, jeux, tableaux de bord.",
     'specs': ["Diagonale : 2,4 pouces", "Résolution : 240 × 320, 262 000 couleurs", "Dalle tactile",
               "Format shield Arduino Uno", "Compatible 3,3 V et 5 V"]},

    # ── Écrans LCD ──
    {'nom': 'Écran LCD 16x2 rétroéclairage bleu', 'prix_source': 2310, 'ref': 'LCD 1602',
     'slug': 'ecran-lcd-16x2-bleu',
     'courte': "Afficheur LCD 2 lignes de 16 caractères, rétroéclairage bleu, contrôleur HD44780.",
     'texte': "Le grand classique pour afficher textes et mesures. Ajoutez un module I2C pour réduire le câblage à 4 fils.",
     'specs': ["2 lignes × 16 caractères", "Contrôleur HD44780 ou compatible", "Alimentation 5 V", "Dimensions : 80 × 35 × 11 mm"]},
    {'nom': 'Écran LCD 16x2 rétroéclairage vert', 'prix_source': 2310, 'ref': 'LCD 1602',
     'slug': 'ecran-lcd-16x2-vert',
     'courte': "Afficheur LCD 2 lignes de 16 caractères, rétroéclairage vert, contrôleur HD44780.",
     'texte': "Version à fond vert du LCD 1602, très lisible en plein jour. Ajoutez un module I2C pour réduire le câblage.",
     'specs': ["2 lignes × 16 caractères", "Contrôleur HD44780 ou compatible", "Alimentation 5 V", "Dimensions : 80 × 35 × 11 mm"]},
    {'nom': 'Écran LCD 16x2 avec module I2C', 'prix_source': 2860, 'ref': 'LCD 1602 I2C',
     'slug': 'ecran-lcd-16x2-i2c',
     'courte': "LCD 2 lignes de 16 caractères blancs sur fond bleu, avec interface I2C : 4 fils suffisent.",
     'texte': "L'interface I2C libère les broches de votre carte. Contraste réglable.",
     'specs': ["2 lignes × 16 caractères", "Interface I2C (adresse 0x20 à 0x27)", "Caractères blancs sur fond bleu",
               "Alimentation 5 V"]},
    {'nom': 'Écran LCD 16x4 rétroéclairage bleu', 'prix_source': 5500, 'ref': 'LCD 1604',
     'slug': 'ecran-lcd-16x4-bleu',
     'courte': "Afficheur LCD 4 lignes de 16 caractères sur fond bleu.",
     'texte': "Deux fois plus de lignes qu'un LCD 1602 pour afficher plusieurs mesures à la fois.",
     'specs': ["4 lignes × 16 caractères", "Rétroéclairage bleu", "Contrôleur HD44780 ou compatible", "Alimentation 5 V"]},
    {'nom': 'Écran LCD 20x4 rétroéclairage bleu', 'prix_source': 4500, 'ref': 'LCD 2004',
     'slug': 'ecran-lcd-20x4-bleu',
     'courte': "Afficheur LCD 4 lignes de 20 caractères, rétroéclairage bleu.",
     'texte': "80 caractères affichables pour les menus et tableaux de bord. Contraste réglable.",
     'specs': ["4 lignes × 20 caractères", "Rétroéclairage bleu", "Contrôleur HD44780 ou compatible", "Alimentation 5 V"]},
    {'nom': 'Écran LCD 20x4 rétroéclairage vert', 'prix_source': 4500, 'ref': 'LCD 2004',
     'slug': 'ecran-lcd-20x4-vert',
     'courte': "Afficheur LCD 4 lignes de 20 caractères, rétroéclairage vert.",
     'texte': "80 caractères affichables, fond vert très lisible. Pour menus, tableaux de bord et appareils de mesure.",
     'specs': ["4 lignes × 20 caractères", "Rétroéclairage vert", "Contrôleur HD44780 ou compatible", "Alimentation 5 V"]},
    {'nom': 'Écran LCD 20x4 I2C rétroéclairage bleu', 'prix_source': 5300, 'ref': 'LCD 2004 I2C',
     'slug': 'ecran-lcd-20x4-i2c-bleu',
     'courte': "LCD 4 lignes de 20 caractères, rétroéclairage bleu, avec interface I2C intégrée.",
     'texte': "Grand afficheur câblé en 4 fils seulement (VCC, GND, SDA, SCL), compatible Arduino, ESP32 et Raspberry Pi.",
     'specs': ["4 lignes × 20 caractères", "Interface I2C", "Rétroéclairage bleu", "Alimentation 5 V"]},
    {'nom': 'Écran LCD 20x4 I2C rétroéclairage vert', 'prix_source': 5300, 'ref': 'LCD 2004 I2C',
     'slug': 'ecran-lcd-20x4-i2c-vert',
     'courte': "LCD 4 lignes de 20 caractères, rétroéclairage vert, avec interface I2C intégrée.",
     'texte': "Grand afficheur câblé en 4 fils seulement (VCC, GND, SDA, SCL), compatible Arduino, ESP32 et Raspberry Pi.",
     'specs': ["4 lignes × 20 caractères", "Interface I2C", "Rétroéclairage vert", "Alimentation 5 V"]},
    {'nom': 'Écran LCD graphique 128x64 rétroéclairage bleu', 'prix_source': 7800, 'ref': 'LCD 12864',
     'slug': 'ecran-lcd-128x64-bleu',
     'courte': "Écran LCD graphique 128 × 64 pixels : textes, courbes, icônes et menus.",
     'texte': "Contrairement aux LCD à caractères, il affiche n'importe quel dessin pixel par pixel : graphiques de mesure, logos, interfaces.",
     'specs': ["Résolution : 128 × 64 pixels", "Rétroéclairage bleu", "Alimentation 5 V"]},
]
