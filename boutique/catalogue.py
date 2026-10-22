"""
Catalogue de composants de la boutique (Électronique, Électricité, Capteurs, Moteurs & Robotique, LED & Afficheurs,
Boutons & Interrupteurs, Relais, Résistances,
Sans fil & Communication, GSM, GPRS & GPS, Équipements de laboratoire,
Câbles & Connecteurs), prix en FCFA.

Chargés MASQUÉS et avec un stock à 0 : l'admin ajoute l'image et la quantité, puis coche « Actif ».
Chargement : bouton « Charger le catalogue » dans l'admin des produits, ou
`python manage.py charger_catalogue_produits`.
Un produit déjà présent (même slug, ou ancien slug listé dans « alias ») n'est jamais dupliqué
et garde son prix, son stock, ses images et sa publication.
"""
from decimal import ROUND_CEILING, Decimal

from django.db import transaction
from django.utils.text import slugify

from .catalogue_afficheurs import AFFICHEURS
from .catalogue_boutons import BOUTONS
from .catalogue_capteurs import CAPTEURS
from .catalogue_moteurs import MOTEURS
from .catalogue_relais import RELAIS
from .catalogue_resistances import RESISTANCES
from .catalogue_sans_fil import SANS_FIL
from .catalogue_gsm_gps import GSM_GPS
from .catalogue_labo import LABO
from .catalogue_cables import CABLES

MAJORATION = 30  # % ajoutés au prix source (catégories reprises de YoupiLab)

CATEGORIES = {
    'electronique': {'nom': 'Électronique', 'icone': 'fas fa-microchip', 'ordre': 1,
                     'description': "Cartes, capteurs, modules et petits composants pour vos montages et projets IoT."},
    'electricite': {'nom': 'Électricité', 'icone': 'fas fa-lightbulb', 'ordre': 2,
                    'description': "Matériel d'installation électrique, de protection et d'énergie solaire."},
    'capteurs': {'nom': 'Capteurs', 'icone': 'fas fa-satellite-dish', 'ordre': 3,
                 'description': "Capteurs et modules de mesure : température, distance, gaz, courant, présence, santé…"},
    'moteurs-robotique': {'nom': 'Moteurs & Robotique', 'icone': 'fas fa-robot', 'ordre': 4,
                          'description': "Servomoteurs, moteurs pas à pas, drivers, châssis et roues pour vos robots."},
    'leds-afficheurs': {'nom': 'LED & Afficheurs', 'icone': 'fas fa-tv', 'ordre': 5,
                        'description': "LED, matrices, afficheurs 7 segments, écrans LCD, OLED et TFT."},
    'boutons-interrupteurs': {'nom': 'Boutons & Interrupteurs', 'icone': 'fas fa-toggle-on', 'ordre': 6,
                              'description': "Boutons poussoirs, interrupteurs, fins de course, claviers et boutons tactiles."},
    'relais': {'nom': 'Relais', 'icone': 'fas fa-plug', 'ordre': 7,
               'description': "Relais, modules relais 5 V / 12 V / 30 A, relais statiques (SSR) et commutateurs connectés."},
    'resistances': {'nom': 'Résistances', 'icone': 'fas fa-wave-square', 'ordre': 8,
                    'description': "Résistances 1/4 W, 1/2 W et 1 W, et kit d'assortiment."},
    'sans-fil': {'nom': 'Sans fil & Communication', 'icone': 'fas fa-wifi', 'ordre': 9,
                 'description': "ESP32, ESP8266, LoRa, Bluetooth, radio 433 MHz, RFID et convertisseurs USB / série."},
    'gsm-gps': {'nom': 'GSM, GPRS & GPS', 'icone': 'fas fa-satellite', 'ordre': 10,
                'description': "Modules GSM / GPRS (SMS, appels, données), récepteurs GPS et antennes."},
    'labo': {'nom': 'Équipements de laboratoire', 'icone': 'fas fa-flask', 'ordre': 11,
             'description': "Protoboards, veroboards, plaques cuivrées, soudure et rangement pour l'atelier électronique."},
    'cables': {'nom': 'Câbles & Connecteurs', 'icone': 'fas fa-link', 'ordre': 12,
               'description': "Jumpers, câbles USB / HDMI / Grove, convertisseurs série, connecteurs et cordons de test."},
}

PRODUITS = {
    'electronique': [
        {'nom': 'Arduino Uno R3', 'prix': 6500, 'ref': 'ATmega328P',
         'courte': "La carte de référence pour apprendre l'électronique et prototyper : simple, robuste et compatible avec des milliers de projets.",
         'texte': "L'Arduino Uno R3 est la carte idéale pour débuter et pour réaliser des prototypes. "
                  "Elle se programme en USB depuis l'IDE Arduino et accepte la plupart des capteurs, écrans et modules du catalogue.",
         'specs': ["Microcontrôleur ATmega328P à 16 MHz", "14 entrées/sorties numériques (dont 6 PWM) et 6 entrées analogiques",
                   "32 Ko de mémoire flash", "Alimentation par USB ou par jack (7 à 12 V recommandés)", "Logique 5 V"]},
        {'nom': 'ESP32', 'prix': 6500, 'ref': 'ESP32-WROOM-32',
         'courte': "Carte Wi-Fi + Bluetooth double cœur pour vos objets connectés, la domotique et le contrôle à distance.",
         'texte': "L'ESP32 réunit un microcontrôleur puissant, le Wi-Fi et le Bluetooth sur une seule carte. "
                  "Parfaite pour envoyer des mesures sur Internet, piloter des relais depuis un téléphone ou créer un serveur web embarqué.",
         'specs': ["Processeur double cœur jusqu'à 240 MHz", "Wi-Fi 2,4 GHz et Bluetooth (classique et BLE)",
                   "Programmable avec l'IDE Arduino ou MicroPython", "Entrées analogiques, PWM, I2C, SPI, UART", "Logique 3,3 V, alimentation par USB"]},
        {'nom': 'PZEM-004T', 'prix': 9000, 'ref': 'PZEM-004T v3.0',
         'courte': "Module de mesure d'énergie AC : tension, courant, puissance, énergie consommée, fréquence et facteur de puissance.",
         'texte': "Le PZEM-004T mesure la consommation électrique d'une installation 220 V et transmet les valeurs à un Arduino ou un ESP32. "
                  "Idéal pour un compteur intelligent, le suivi de consommation ou la facturation d'énergie.",
         'specs': ["Tension mesurée : 80 à 260 V AC", "Courant jusqu'à 100 A avec tore (transformateur de courant)",
                   "Mesures : tension, courant, puissance, énergie, fréquence, facteur de puissance", "Communication série TTL (Modbus RTU)"]},
        {'nom': 'Monnayeur électronique CH-926', 'prix': 25000, 'ref': 'CH-926',
         'courte': "Accepteur de pièces programmable (jusqu'à 6 types de pièces) pour distributeurs, bornes et machines à pièces.",
         'texte': "Le monnayeur CH-926 reconnaît les pièces par leur taille, leur épaisseur et leur matière, puis envoie des impulsions "
                  "à votre carte (Arduino, ESP32…). Idéal pour un distributeur automatique, une borne de recharge ou un jeu à pièces.",
         'specs': ["Jusqu'à 6 types de pièces programmables", "Sortie par impulsions (nombre réglable par pièce)",
                   "Alimentation 12 V DC", "Rejet automatique des pièces non reconnues"]},
        {'nom': 'Module relais 2 canaux', 'prix': 1500, 'ref': '',
         'courte': "Deux relais 5 V pilotables par Arduino ou ESP32 pour commander lampes, prises, pompes ou moteurs.",
         'texte': "Ce module permet à une carte électronique de commander deux appareils alimentés en 220 V ou en courant continu. "
                  "Chaque canal possède sa LED témoin.",
         'specs': ["2 relais, bobine 5 V", "Contacts jusqu'à 10 A sous 250 V AC", "Contacts NO / NF / commun sur bornier à vis",
                   "Entrées compatibles Arduino et ESP32", "LED témoin par canal"]},
        {'nom': 'Relais 5V', 'prix': 750, 'ref': 'SRD-05VDC-SL-C', 'alias': ['relay-5v'],
         'courte': "Relais 5 V à souder pour commuter une charge jusqu'à 10 A depuis un circuit électronique.",
         'texte': "Relais électromécanique classique à intégrer sur vos circuits imprimés. "
                  "À commander via un transistor (ex. BC547) avec une diode de roue libre (ex. 1N4007).",
         'specs': ["Bobine 5 V DC", "Contacts jusqu'à 10 A sous 250 V AC", "Un contact inverseur (NO / NF)"]},
        {'nom': 'DHT22', 'prix': 4500, 'ref': 'AM2302',
         'courte': "Capteur numérique de température et d'humidité, précis, pour stations météo, serres et domotique.",
         'texte': "Le DHT22 mesure la température et l'humidité de l'air et les transmet sur un seul fil de données. "
                  "Plus précis que le DHT11, il convient aux serres, couveuses, salles serveurs et stations météo.",
         'specs': ["Température : -40 à 80 °C (précision ±0,5 °C)", "Humidité : 0 à 100 % HR (précision ±2 à 5 %)",
                   "Alimentation 3,3 à 6 V", "Une mesure toutes les 2 secondes"]},
        {'nom': 'MQ-2', 'prix': 2500, 'ref': 'MQ-2',
         'courte': "Capteur de gaz et de fumée (GPL, butane, propane, méthane, hydrogène) pour détecteurs et alarmes.",
         'texte': "Le module MQ-2 détecte les fuites de gaz domestique et la fumée. "
                  "Sa sortie analogique donne le niveau de concentration et sa sortie numérique déclenche une alerte à un seuil réglable.",
         'specs': ["Détection : GPL, butane, propane, méthane, hydrogène, fumée", "Alimentation 5 V",
                   "Sortie analogique + sortie numérique (seuil réglable par potentiomètre)", "Temps de chauffe conseillé avant mesure fiable"]},
        {'nom': 'Capteur de débit YF-S201', 'prix': 6000, 'ref': 'YF-S201',
         'courte': "Débitmètre à effet Hall pour mesurer le débit et le volume d'eau (1 à 30 L/min).",
         'texte': "Le YF-S201 se place sur une canalisation et envoie des impulsions proportionnelles au débit d'eau. "
                  "Idéal pour un compteur d'eau intelligent, un distributeur d'eau ou le suivi d'irrigation.",
         'specs': ["Débit mesuré : 1 à 30 L/min", "Alimentation 5 à 18 V DC", "Sortie par impulsions (environ 450 impulsions par litre)",
                   "Raccord fileté 1/2 pouce"]},
        {'nom': 'Écran LCD I2C 16x4', 'prix': 5000, 'ref': 'LCD 1604 + PCF8574',
         'courte': "Afficheur LCD 4 lignes de 16 caractères avec module I2C : seulement 2 fils de données à câbler.",
         'texte': "Cet écran affiche textes et valeurs (mesures, menus, messages) sur 4 lignes. "
                  "Le module I2C déjà monté réduit le câblage à 4 fils (alimentation + SDA/SCL).",
         'specs': ["4 lignes × 16 caractères, rétroéclairage", "Interface I2C (adresse courante 0x27 ou 0x3F)",
                   "Contraste réglable par potentiomètre", "Alimentation 5 V, compatible Arduino et ESP32"]},
        {'nom': 'Écran LCD 20x4 + module I2C', 'prix': 6500, 'ref': 'LCD 2004 + PCF8574',
         'courte': "Grand afficheur LCD 4 lignes de 20 caractères avec module I2C, pour tableaux de bord et menus.",
         'texte': "Avec 80 caractères affichables, le LCD 20x4 convient aux interfaces plus riches : plusieurs mesures à la fois, menus, état d'un système. "
                  "Fourni avec son module I2C pour un câblage en 4 fils.",
         'specs': ["4 lignes × 20 caractères, rétroéclairage", "Module I2C (adresse courante 0x27 ou 0x3F)",
                   "Contraste réglable par potentiomètre", "Alimentation 5 V"]},
        {'nom': 'Buzzer actif 5V', 'prix': 700, 'ref': '',
         'courte': "Buzzer avec oscillateur intégré : il sonne dès qu'on l'alimente, idéal pour les alarmes et signaux sonores.",
         'texte': "Le buzzer actif émet un son continu dès qu'il reçoit 5 V : une simple sortie numérique suffit pour le déclencher. "
                  "Utile pour les alarmes, minuteries et confirmations sonores.",
         'specs': ["Alimentation 5 V DC", "Oscillateur intégré (pas besoin de signal PWM)", "Respecter la polarité (+ / -)"]},
        {'nom': 'LED rouge', 'prix': 100, 'ref': 'LED 5 mm',
         'courte': "LED 5 mm rouge pour voyants, signalisation et premiers montages.",
         'texte': "Diode électroluminescente rouge de 5 mm. Toujours la brancher avec une résistance en série (ex. 220 Ω).",
         'specs': ["Diamètre 5 mm", "Tension directe environ 2 V", "Courant nominal 20 mA", "Patte longue = anode (+)"]},
        {'nom': 'LED verte', 'prix': 100, 'ref': 'LED 5 mm',
         'courte': "LED 5 mm verte pour voyants « marche / OK » et signalisation.",
         'texte': "Diode électroluminescente verte de 5 mm. Toujours la brancher avec une résistance en série (ex. 220 Ω).",
         'specs': ["Diamètre 5 mm", "Tension directe environ 2 à 3 V", "Courant nominal 20 mA", "Patte longue = anode (+)"]},
        {'nom': 'LED bleue', 'prix': 100, 'ref': 'LED 5 mm',
         'courte': "LED 5 mm bleue lumineuse pour voyants et décoration de vos montages.",
         'texte': "Diode électroluminescente bleue de 5 mm. Toujours la brancher avec une résistance en série (ex. 220 Ω).",
         'specs': ["Diamètre 5 mm", "Tension directe environ 3 V", "Courant nominal 20 mA", "Patte longue = anode (+)"]},
        {'nom': 'Transistor BC547', 'prix': 400, 'ref': 'BC547',
         'courte': "Transistor NPN polyvalent pour commander un relais, un buzzer ou une LED depuis une carte.",
         'texte': "Le BC547 sert d'interrupteur ou d'amplificateur pour les petits courants. "
                  "Il permet par exemple à un Arduino de commander la bobine d'un relais.",
         'specs': ["Type NPN, boîtier TO-92", "Tension collecteur-émetteur max : 45 V", "Courant collecteur max : 100 mA"]},
        {'nom': 'Diode 1N4007 + circuit imprimé', 'prix': 10200, 'ref': '1N4007',
         'courte': "Diodes de redressement 1N4007 et circuit imprimé pour réaliser vos montages d'alimentation et de protection.",
         'texte': "La 1N4007 est la diode de redressement la plus utilisée : ponts redresseurs, protection contre l'inversion de polarité, "
                  "diode de roue libre sur les relais. Fournie avec un circuit imprimé pour monter proprement votre circuit.",
         'specs': ["Diode 1N4007 : 1 A, 1000 V", "Circuit imprimé inclus", "Usages : redressement, roue libre, protection de polarité"]},
        {'nom': 'Résistance 220 Ω', 'prix': 50, 'ref': '220 Ω 1/4 W',
         'courte': "Résistance 220 ohms 1/4 W, la valeur classique pour limiter le courant des LED.",
         'texte': "Résistance à couche de 220 Ω (rouge-rouge-marron). C'est la valeur à placer en série avec une LED sur une sortie 5 V.",
         'specs': ["Valeur : 220 Ω", "Puissance : 1/4 W", "Code couleurs : rouge, rouge, marron"]},
        {'nom': 'Bouton poussoir reset', 'prix': 500, 'ref': '',
         'courte': "Bouton poussoir à contact momentané pour réinitialiser une carte ou servir d'entrée utilisateur.",
         'texte': "Le contact se ferme uniquement pendant l'appui. Utilisé pour le reset d'un montage, un bouton de validation ou de menu.",
         'specs': ["Contact momentané (fermé pendant l'appui)", "Montage sur protoboard ou circuit imprimé"]},
        {'nom': 'Bornier vis 2P/3P', 'prix': 200, 'ref': 'Pas 5,08 mm',
         'courte': "Bornier à vis 2 ou 3 points à souder, pour raccorder solidement des fils sur un circuit imprimé.",
         'texte': "Le bornier à vis permet de brancher et débrancher les fils d'alimentation ou de capteurs sans soudure. "
                  "Les modèles s'emboîtent pour obtenir plus de points.",
         'specs': ["2 ou 3 points de connexion (à préciser à la commande)", "Pas de 5,08 mm, à souder sur circuit imprimé", "Serrage par vis"]},
        {'nom': 'Protoboard', 'prix': 1500, 'ref': '',
         'courte': "Plaque d'essai sans soudure pour tester vos circuits rapidement avant de les souder.",
         'texte': "La protoboard (breadboard) permet de câbler composants et modules par simple insertion. "
                  "Indispensable pour apprendre, tester et modifier un montage.",
         'specs': ["Montage sans soudure, réutilisable", "Rails d'alimentation sur les côtés", "Compatible avec les jumpers Dupont"]},
        {'nom': 'Jumpers M-F', 'prix': 50, 'ref': 'Dupont M-F',
         'courte': "Fil de connexion Dupont mâle-femelle pour relier modules et cartes.",
         'texte': "Fil de liaison avec une broche mâle d'un côté et un connecteur femelle de l'autre : "
                  "idéal pour brancher un capteur ou un module sur une protoboard.",
         'specs': ["Connecteurs mâle / femelle type Dupont", "Prix à l'unité"]},
        {'nom': 'Jumpers M-M', 'prix': 50, 'ref': 'Dupont M-M',
         'courte': "Fil de connexion Dupont mâle-mâle pour câbler sur protoboard.",
         'texte': "Fil de liaison avec une broche mâle à chaque extrémité, pour relier les composants sur une protoboard ou aux connecteurs d'une carte Arduino.",
         'specs': ["Connecteurs mâle / mâle type Dupont", "Prix à l'unité"]},
        {'nom': 'Convertisseur Buck LM2596', 'prix': 2500, 'ref': 'LM2596',
         'courte': "Abaisseur de tension réglable (ex. 12 V vers 5 V) pour alimenter vos cartes depuis une batterie.",
         'texte': "Le module LM2596 abaisse une tension continue avec un bon rendement. "
                  "Il permet par exemple d'alimenter un ESP32 ou un Arduino à partir d'une batterie ou d'un panneau solaire 12 V.",
         'specs': ["Entrée : 4 à 40 V DC", "Sortie réglable : 1,25 à 35 V DC", "Courant max : 3 A (2 A en continu conseillé)",
                   "Réglage par potentiomètre multitour"]},
        {'nom': 'Adaptateur secteur 12V/2A', 'prix': 3500, 'ref': '12 V 2 A',
         'courte': "Alimentation secteur 220 V vers 12 V DC 2 A pour vos montages, rubans LED et modules.",
         'texte': "Bloc d'alimentation pour faire fonctionner vos projets sur le secteur : cartes, électrovannes, rubans LED, petits moteurs.",
         'specs': ["Entrée : 100 à 240 V AC", "Sortie : 12 V DC, 2 A", "Connecteur jack"]},
        {'nom': 'Chargeur Android', 'prix': 1500, 'ref': '',
         'courte': "Chargeur secteur USB 5 V pour téléphone, qui sert aussi à alimenter Arduino, ESP32 et petits modules.",
         'texte': "Chargeur USB pour smartphone Android. Pratique aussi pour alimenter une carte de développement en 5 V par son port USB.",
         'specs': ["Entrée : 220 V AC", "Sortie USB 5 V"]},
        {'nom': 'Colle à pistolet', 'prix': 400, 'ref': '',
         'courte': "Bâton de colle thermofusible pour fixer composants, câbles et boîtiers.",
         'texte': "Colle thermofusible pour pistolet à colle : fixation rapide des modules dans un boîtier, maintien des câbles, isolation de soudures.",
         'specs': ["Pour pistolet à colle", "Prise rapide en refroidissant"]},
        {'nom': 'Étain à souder', 'prix': 1000, 'ref': '',
         'courte': "Fil d'étain avec flux pour souder vos composants électroniques.",
         'texte': "Fil de soudure pour fer à souder, avec flux intégré pour des soudures propres et brillantes sur circuits imprimés et fils.",
         'specs': ["Flux intégré", "Pour soudure électronique au fer"]},
    ],
    'electricite': [
        {'nom': 'Panneau solaire 12V', 'prix': 10000, 'ref': '12 V',
         'courte': "Panneau photovoltaïque 12 V pour recharger une batterie et alimenter éclairage et petits appareils.",
         'texte': "Panneau solaire pour systèmes 12 V : éclairage autonome, recharge de batterie, alimentation de capteurs ou de pompes. "
                  "À associer à un régulateur solaire.",
         'specs': ["Tension nominale 12 V", "Usage extérieur", "À utiliser avec un régulateur de charge"]},
        {'nom': 'Panneau solaire 20W + contrôleur', 'prix': 12000, 'ref': '20 W',
         'courte': "Kit panneau solaire 20 W avec son contrôleur de charge, prêt pour un petit système autonome.",
         'texte': "Ensemble panneau + contrôleur pour démarrer un petit système solaire : éclairage, recharge de téléphone, alimentation de projets IoT.",
         'specs': ["Panneau 20 W", "Contrôleur de charge inclus", "Pour batterie 12 V"]},
        {'nom': 'Batterie 12V', 'prix': 12000, 'ref': '12 V',
         'courte': "Batterie 12 V pour stocker l'énergie solaire ou servir de secours à vos installations.",
         'texte': "Batterie rechargeable 12 V pour kits solaires, alarmes, éclairage de secours et projets électroniques autonomes.",
         'specs': ["Tension 12 V", "Rechargeable", "À utiliser avec un régulateur pour une recharge solaire"]},
        {'nom': 'Régulateur solaire', 'prix': 5000, 'ref': '',
         'courte': "Contrôleur de charge qui protège la batterie entre le panneau solaire et vos appareils.",
         'texte': "Le régulateur gère la charge de la batterie à partir du panneau solaire et coupe la sortie si la batterie est trop déchargée.",
         'specs': ["Pour systèmes 12 V", "Protection contre la surcharge et la décharge profonde", "Bornes panneau / batterie / sortie"]},
        {'nom': 'Disjoncteur 10A', 'prix': 1500, 'ref': '10 A',
         'courte': "Disjoncteur modulaire 10 A pour protéger les circuits d'éclairage.",
         'texte': "Protège un circuit contre les surcharges et les courts-circuits. Calibre adapté aux circuits d'éclairage.",
         'specs': ["Calibre 10 A", "Montage sur rail DIN", "Protection surcharge et court-circuit"]},
        {'nom': 'Disjoncteur PN 16A', 'prix': 1000, 'ref': 'PN 16 A',
         'courte': "Disjoncteur phase + neutre 16 A pour les circuits de prises de courant.",
         'texte': "Disjoncteur modulaire phase-neutre qui protège les circuits de prises contre les surcharges et les courts-circuits.",
         'specs': ["Calibre 16 A", "Phase + neutre", "Montage sur rail DIN"]},
        {'nom': 'Disjoncteur PN 20A', 'prix': 1500, 'ref': 'PN 20 A',
         'courte': "Disjoncteur phase + neutre 20 A pour circuits de prises et appareils plus puissants.",
         'texte': "Disjoncteur modulaire phase-neutre pour les circuits plus chargés (prises de cuisine, appareils de puissance).",
         'specs': ["Calibre 20 A", "Phase + neutre", "Montage sur rail DIN"]},
        {'nom': 'Disjoncteur différentiel 25A/30mA', 'prix': 3000, 'ref': '25 A 30 mA',
         'courte': "Différentiel 30 mA qui coupe le courant en cas de fuite : protection des personnes contre l'électrocution.",
         'texte': "Le disjoncteur différentiel détecte les fuites de courant vers la terre et coupe immédiatement le circuit. "
                  "Indispensable pour la sécurité d'une installation domestique.",
         'specs': ["Calibre 25 A", "Sensibilité 30 mA (protection des personnes)", "Montage sur rail DIN"]},
        {'nom': 'Coffret électrique de 4', 'prix': 1500, 'ref': '4 modules',
         'courte': "Petit coffret pour 4 modules (disjoncteurs) avec rail DIN, pour un tableau électrique compact.",
         'texte': "Coffret pour regrouper et protéger jusqu'à 4 appareils modulaires : disjoncteurs, différentiel.",
         'specs': ["Capacité : 4 modules", "Rail DIN intégré"]},
        {'nom': 'Barrette de coupure', 'prix': 1500, 'ref': '',
         'courte': "Barrette de coupure de terre pour raccorder et contrôler la prise de terre de l'installation.",
         'texte': "Placée entre le piquet de terre et le tableau, la barrette de coupure permet de déconnecter la terre pour mesurer sa résistance.",
         'specs': ["Raccordement du conducteur de terre", "Permet la mesure de la prise de terre"]},
        {'nom': 'Piquet de terre', 'prix': 500, 'ref': '',
         'courte': "Piquet métallique à enfoncer dans le sol pour réaliser la prise de terre de l'installation.",
         'texte': "Le piquet de terre évacue les courants de défaut vers le sol. À relier à la barrette de coupure par un câble de terre (ex. câble nu).",
         'specs': ["À enfoncer dans le sol", "À raccorder au conducteur de terre"]},
        {'nom': 'Câble souple 0,5 mm²', 'prix': 300, 'ref': '0,5 mm²',
         'courte': "Câble souple de 0,5 mm² pour le câblage de petits appareils, voyants et montages basse puissance.",
         'texte': "Câble multibrins souple, facile à manipuler, pour les liaisons de faible puissance et le câblage électronique.",
         'specs': ["Section 0,5 mm²", "Âme souple multibrins"]},
        {'nom': 'Fils électriques', 'prix': 300, 'ref': '', 'alias': ['fil-electrique'],
         'courte': "Fils électriques pour vos raccordements et montages.",
         'texte': "Fils de câblage pour les raccordements courants, montages et réparations.",
         'specs': ["Isolant PVC", "Plusieurs couleurs selon disponibilité"]},
        {'nom': 'Câble nu 2,5 mm (au mètre)', 'prix': 1500, 'ref': '2,5 mm',
         'courte': "Câble de cuivre nu, vendu au mètre, pour la liaison de terre.",
         'texte': "Conducteur en cuivre nu utilisé pour relier le piquet de terre à la barrette de coupure.",
         'specs': ["Cuivre nu", "Section 2,5 mm²", "Vendu au mètre"]},
        {'nom': 'Câble VGV rigide 1,5 mm (rouleau)', 'prix': 35000, 'ref': 'VGV 1,5 mm²',
         'courte': "Rouleau de câble VGV rigide 1,5 mm² pour les circuits d'éclairage.",
         'texte': "Câble rigide sous gaine pour les installations intérieures. La section 1,5 mm² est adaptée aux circuits d'éclairage.",
         'specs': ["Section 1,5 mm²", "Âme rigide", "Vendu au rouleau"]},
        {'nom': 'Câble VGV rigide 2,5 mm (rouleau)', 'prix': 45000, 'ref': 'VGV 2,5 mm²',
         'courte': "Rouleau de câble VGV rigide 2,5 mm² pour les circuits de prises de courant.",
         'texte': "Câble rigide sous gaine pour les installations intérieures. La section 2,5 mm² est adaptée aux circuits de prises.",
         'specs': ["Section 2,5 mm²", "Âme rigide", "Vendu au rouleau"]},
        {'nom': 'Câble aluminium alimentation (rouleau)', 'prix': 9000, 'ref': '',
         'courte': "Rouleau de câble aluminium pour l'alimentation (branchement du compteur au bâtiment).",
         'texte': "Câble d'alimentation en aluminium, léger et économique, pour l'arrivée du courant jusqu'au tableau.",
         'specs': ["Âme aluminium", "Vendu au rouleau"]},
        {'nom': 'Domino de 16', 'prix': 800, 'ref': '16 mm²',
         'courte': "Barrette de dominos pour raccorder des conducteurs jusqu'à 16 mm².",
         'texte': "Barrette de connexion à vis pour relier solidement plusieurs conducteurs, découpable selon le besoin.",
         'specs': ["Pour sections jusqu'à 16 mm²", "Serrage par vis", "Barrette sécable"]},
        {'nom': 'Domino de 25', 'prix': 1000, 'ref': '25 mm²',
         'courte': "Barrette de dominos pour raccorder des conducteurs de forte section jusqu'à 25 mm².",
         'texte': "Barrette de connexion à vis pour les câbles de forte section (arrivée d'alimentation, tableau).",
         'specs': ["Pour sections jusqu'à 25 mm²", "Serrage par vis", "Barrette sécable"]},
        {'nom': 'Scotch noir', 'prix': 200, 'ref': '',
         'courte': "Ruban adhésif isolant pour protéger et repérer vos raccordements électriques.",
         'texte': "Ruban isolant en PVC pour isoler les épissures, protéger les raccords et regrouper les câbles.",
         'specs': ["Ruban isolant PVC", "Couleur noire"]},
        {'nom': 'Boîte de dérivation', 'prix': 3000, 'ref': '',
         'courte': "Boîte de dérivation pour regrouper et protéger les raccordements de l'installation.",
         'texte': "Boîte pour réaliser les dérivations de circuits à l'abri des chocs et de la poussière.",
         'specs': ["Avec couvercle", "Entrées de câbles"]},
        {'nom': 'Boîte de dérivation petit', 'prix': 700, 'ref': 'Petit modèle',
         'courte': "Petite boîte de dérivation pour quelques raccordements.",
         'texte': "Petit modèle de boîte de dérivation, pour un ou deux raccordements.",
         'specs': ["Petit format", "Avec couvercle"]},
        {'nom': 'Boîte de dérivation moyen', 'prix': 1200, 'ref': 'Moyen modèle',
         'courte': "Boîte de dérivation de taille moyenne pour vos raccordements de circuits.",
         'texte': "Modèle moyen, adapté à la plupart des dérivations d'une installation domestique.",
         'specs': ["Format moyen", "Avec couvercle"]},
        {'nom': 'Boîte de dérivation grand', 'prix': 2500, 'ref': 'Grand modèle',
         'courte': "Grande boîte de dérivation pour de nombreux raccordements.",
         'texte': "Grand modèle pour regrouper plusieurs circuits et de nombreux raccordements.",
         'specs': ["Grand format", "Avec couvercle"]},
        {'nom': 'Boîte attache de 6', 'prix': 500, 'ref': '',
         'courte': "Boîte d'attaches pour fixer proprement les câbles au mur.",
         'texte': "Attaches de fixation pour maintenir les câbles le long des murs et plafonds.",
         'specs': ["Taille 6", "Vendu à la boîte"]},
        {'nom': 'Cheville & vis', 'prix': 800, 'ref': '',
         'courte': "Chevilles et vis pour fixer boîtes, coffrets et appareillages au mur.",
         'texte': "Lot de chevilles et vis pour la fixation murale de votre matériel électrique.",
         'specs': ["Chevilles + vis", "Fixation murale"]},
        {'nom': 'Boîtier étanche IP54', 'prix': 6500, 'ref': 'IP54',
         'courte': "Boîtier étanche IP54 pour protéger vos montages et raccordements installés en extérieur.",
         'texte': "Protège cartes électroniques, raccordements et modules contre la poussière et les projections d'eau.",
         'specs': ["Indice de protection IP54 (poussière et projections d'eau)", "Pour usage extérieur abrité"]},
        {'nom': 'Lampe 220V 3W', 'prix': 1000, 'ref': '3 W',
         'courte': "Ampoule 220 V 3 W économique pour l'éclairage d'appoint.",
         'texte': "Ampoule basse consommation de 3 W pour couloirs, veilleuses et petits espaces.",
         'specs': ["Tension 220 V", "Puissance 3 W"]},
        {'nom': 'Lampe 220V 5W', 'prix': 1500, 'ref': '5 W',
         'courte': "Ampoule 220 V 5 W économique pour l'éclairage des pièces.",
         'texte': "Ampoule basse consommation de 5 W pour chambres, bureaux et petites pièces.",
         'specs': ["Tension 220 V", "Puissance 5 W"]},
        {'nom': 'Douille', 'prix': 500, 'ref': '',
         'courte': "Douille pour ampoule, à raccorder sur le circuit d'éclairage.",
         'texte': "Support d'ampoule à visser au plafond ou au mur et à raccorder au circuit d'éclairage.",
         'specs': ["Pour ampoule 220 V", "Bornes de raccordement"]},
        {'nom': 'Prise encastrée', 'prix': 500, 'ref': '',
         'courte': "Prise de courant à encastrer pour une finition propre.",
         'texte': "Prise de courant 220 V à encastrer dans une boîte d'encastrement.",
         'specs': ["220 V", "Montage encastré"]},
        {'nom': 'Prise encastrée étanche', 'prix': 1000, 'ref': '',
         'courte': "Prise encastrée avec clapet de protection pour les pièces humides et l'extérieur abrité.",
         'texte': "Prise de courant protégée contre les projections d'eau, pour salle de bain, cuisine, terrasse.",
         'specs': ["220 V", "Clapet de protection", "Montage encastré"]},
        {'nom': 'Interrupteur C1', 'prix': 500, 'ref': 'C1',
         'courte': "Interrupteur simple allumage : commande un point lumineux depuis un seul endroit.",
         'texte': "L'interrupteur C1 (simple allumage) allume et éteint une lampe ou un groupe de lampes depuis un seul endroit.",
         'specs': ["Simple allumage", "Commande d'un circuit d'éclairage", "Vendu à l'unité"]},
        {'nom': 'Interrupteur C5 encastré', 'prix': 500, 'ref': 'C5',
         'courte': "Interrupteur double allumage encastré : commande deux circuits d'éclairage séparés.",
         'texte': "L'interrupteur C5 (double allumage) commande deux lampes ou groupes de lampes indépendants à partir d'un seul appareil.",
         'specs': ["Double allumage", "Montage encastré", "Vendu à l'unité"]},
        {'nom': 'Interrupteur C5 apparent', 'prix': 500, 'ref': 'C5',
         'courte': "Interrupteur double allumage en saillie, sans encastrement.",
         'texte': "L'interrupteur C5 (double allumage) en version apparente se fixe directement sur le mur, sans boîte d'encastrement.",
         'specs': ["Double allumage", "Montage apparent (en saillie)", "Vendu à l'unité"]},
        {'nom': 'Interrupteur C6 encastré', 'prix': 800, 'ref': 'C6',
         'courte': "Interrupteur va-et-vient encastré : commande une lampe depuis deux endroits.",
         'texte': "L'interrupteur C6 (va-et-vient) permet de commander une même lampe depuis deux endroits, par exemple les deux bouts d'un couloir.",
         'specs': ["Va-et-vient", "Montage encastré", "Vendu à l'unité"]},
        {'nom': 'Interrupteur C7 encastré', 'prix': 1000, 'ref': 'C7',
         'courte': "Interrupteur permutateur encastré : commande une lampe depuis trois endroits ou plus.",
         'texte': "L'interrupteur C7 (permutateur) permet de commander une même lampe depuis trois endroits ou plus, par exemple dans un long couloir ou une cage d'escalier.",
         'specs': ["Permutateur (intermédiaire)", "Montage encastré", "Vendu à l'unité"]},
        {'nom': 'Électrovanne 12V DC', 'prix': 4500, 'ref': '12 V DC',
         'courte': "Vanne commandée électriquement en 12 V pour automatiser l'arrosage ou la distribution d'eau.",
         'texte': "L'électrovanne ouvre ou ferme le passage de l'eau sur commande : arrosage automatique, distributeur d'eau, remplissage de réservoir. "
                  "Pilotable par Arduino ou ESP32 à travers un relais.",
         'specs': ["Alimentation 12 V DC", "Commande par relais", "Pour l'eau"]},
        {'nom': 'Pompe 12V 4200 L/H', 'prix': 11000, 'ref': '12 V 4200 L/h',
         'courte': "Pompe à eau 12 V d'un débit de 4200 L/h, compatible alimentation solaire.",
         'texte': "Pompe à eau en courant continu pour l'irrigation, le transfert d'eau ou les fontaines, alimentable par batterie ou kit solaire.",
         'specs': ["Alimentation 12 V DC", "Débit jusqu'à 4200 L/h", "Compatible batterie et kit solaire"]},
        {'nom': 'Ventilateur 12V', 'prix': 2500, 'ref': '12 V DC',
         'courte': "Ventilateur 12 V pour refroidir boîtiers, alimentations et montages électroniques.",
         'texte': "Ventilateur en courant continu pour évacuer la chaleur d'un boîtier ou d'un tableau, alimentable par batterie ou adaptateur 12 V.",
         'specs': ["Alimentation 12 V DC", "Pour refroidissement de boîtiers"]},
        {'nom': 'Tuyauterie PVC + raccords', 'prix': 5000, 'ref': 'PVC',
         'courte': "Lot de tuyauterie PVC et raccords pour vos installations d'eau, d'arrosage ou de pompage.",
         'texte': "Tuyaux et raccords PVC pour relier pompe, électrovanne et capteur de débit dans vos projets d'eau.",
         'specs': ["Tuyau PVC + raccords", "Pour installations d'eau, arrosage et pompage"]},
    ],
}


def prix_majore(prix_source, pourcentage=MAJORATION):
    """Prix source (entier ou décimal) + pourcentage, arrondi au multiple de 5 FCFA supérieur."""
    prix = Decimal(str(prix_source)) * (100 + pourcentage) / 500
    return int(prix.to_integral_value(rounding=ROUND_CEILING)) * 5


# « prix_min » : plancher de prix (ex. 50 FCFA pour les LED vendues moins cher chez la source)
# « prix_fixe » : prix KcoMat imposé, sans majoration (ex. jumpers à 50 FCFA l'unité)
for _categorie, _fiches in (('capteurs', CAPTEURS), ('moteurs-robotique', MOTEURS), ('leds-afficheurs', AFFICHEURS),
                            ('boutons-interrupteurs', BOUTONS), ('relais', RELAIS),
                            ('resistances', RESISTANCES), ('sans-fil', SANS_FIL),
                            ('gsm-gps', GSM_GPS), ('labo', LABO), ('cables', CABLES)):
    PRODUITS[_categorie] = [{**fiche, 'prix': fiche.get('prix_fixe') or max(prix_majore(fiche['prix_source']),
                                                                             fiche.get('prix_min', 0))}
                            for fiche in _fiches]


def slug_produit(fiche):
    return fiche.get('slug') or slugify(fiche['nom'])


def description(fiche):
    """Texte complet de la fiche produit : présentation puis caractéristiques à puces."""
    lignes = '\n'.join(f"• {spec}" for spec in fiche['specs'])
    return f"{fiche['texte']}\n\nCaractéristiques :\n{lignes}"


def nombre_produits():
    """Produits distincts : une fiche dont l'alias désigne une autre fiche du catalogue (ex. DHT22) ne compte qu'une fois."""
    fiches = [fiche for fiches in PRODUITS.values() for fiche in fiches]
    slugs = {slug_produit(fiche) for fiche in fiches}
    return sum(1 for fiche in fiches if not slugs & set(fiche.get('alias', [])))


@transaction.atomic
def charger_catalogue(force=False):
    """
    Crée les catégories et les produits du catalogue absents (masqués, stock à 0, sans image).
    force=True réécrit aussi les textes des produits du catalogue déjà présents
    (sans toucher au prix, au stock, aux images ni à la publication).
    Retourne (créés, mis à jour, inchangés).
    """
    from .models import CategorieProduit, Produit

    crees, maj, inchangees = 0, 0, 0
    for slug_categorie, fiches in PRODUITS.items():
        infos = CATEGORIES[slug_categorie]
        categorie, _ = CategorieProduit.objects.get_or_create(
            slug=slug_categorie,
            defaults={'nom': infos['nom'], 'icone': infos['icone'], 'ordre': infos['ordre'], 'description': infos['description']},
        )
        for fiche in fiches:
            champs = {
                'categorie': categorie,
                'reference': fiche['ref'],
                'description_courte': fiche['courte'],
                'description': description(fiche),
            }
            slugs = [slug_produit(fiche), *fiche.get('alias', [])]
            produit = Produit.objects.filter(slug__in=slugs).first()
            if produit is None:
                Produit.objects.create(nom=fiche['nom'], slug=slugs[0], prix=fiche['prix'], stock=0, actif=False, **champs)
                crees += 1
            elif force:
                for nom, valeur in champs.items():
                    setattr(produit, nom, valeur)
                produit.save()
                maj += 1
            else:
                inchangees += 1
    return crees, maj, inchangees
