"""
Catégorie « GSM, GPRS & GPS » du catalogue de la boutique.

Liste établie d'après la catégorie GSM / GPRS / GPS de components.youpilab.com (octobre 2026) :
`prix_source` est le prix affiché là-bas ; le prix de vente KcoMat est majoré de 30 %
(voir `catalogue.prix_majore`). Textes rédigés pour KcoMat à partir des caractéristiques techniques.
"""

_SPECS_SIM800L = ["Réseau 2G GSM / GPRS quadri-bande (850 / 900 / 1800 / 1900 MHz)", "Appels, SMS et données GPRS",
                  "Commandes AT par port série", "Emplacement micro SIM", "Alimentation 3,4 à 4,4 V, pics de courant jusqu'à 2 A"]

GSM_GPS = [
    # ── GSM / GPRS ──
    {'nom': 'Module GSM SIM800L', 'prix_source': 6500, 'ref': 'SIM800L', 'slug': 'module-gsm-sim800l',
     'courte': "Mini module GSM 2G : envoyez des SMS, passez des appels et transmettez des données depuis un Arduino.",
     'texte': "Le SIM800L ajoute le réseau mobile à vos projets : alertes par SMS, commande à distance d'un portail ou d'une pompe, "
              "envoi de mesures sur Internet. Antenne fournie ; prévoir une alimentation capable de fournir 2 A en pointe.",
     'specs': _SPECS_SIM800L},
    {'nom': 'Module GSM SIM800L rouge', 'prix_source': 5400, 'ref': 'SIM800L', 'slug': 'module-gsm-sim800l-rouge',
     'courte': "Module GSM 2G SIM800L (version rouge) pour SMS, appels et données GPRS depuis un microcontrôleur.",
     'texte': "Version économique du SIM800L, avec mini antenne. Prévoir une alimentation dédiée capable de fournir 2 A en pointe.",
     'specs': _SPECS_SIM800L},
    {'nom': 'Module GSM SIM800L V2.0 5V', 'prix_source': 8000, 'ref': 'SIM800L V2.0', 'slug': 'module-gsm-sim800l-v2-5v',
     'courte': "SIM800L sur carte avec régulateur et adaptation de niveaux : se branche directement en 5 V sur un Arduino.",
     'texte': "Plus simple à utiliser que le SIM800L nu : pas de convertisseur de tension à ajouter. "
              "Idéal pour débuter avec les SMS et le GPRS.",
     'specs': ["Réseau 2G GSM / GPRS quadri-bande", "Alimentation 5 V (régulateur intégré)", "Niveaux logiques compatibles 5 V",
               "Appels, SMS et données GPRS", "Commandes AT par port série"]},
    {'nom': 'Module GSM SIM900', 'prix_source': 10900, 'ref': 'SIM900', 'slug': 'module-gsm-sim900',
     'courte': "Carte GSM / GPRS SIM900 compatible Arduino : SMS, appels, MMS et connexion Internet TCP/UDP.",
     'texte': "Module robuste et très documenté, avec pile TCP/UDP intégrée et sorties audio : alarmes, télécommande par SMS, télémétrie.",
     'specs': ["Réseau 2G GSM / GPRS quadri-bande", "Appels, SMS, MMS et GPRS (TCP / UDP)", "Commandes AT par port série",
               "Compatible Arduino"]},
    {'nom': 'Module GSM GPRS IOT-GA6-B', 'prix_source': 6085, 'ref': 'GA6-B', 'slug': 'module-gsm-ga6-b',
     'courte': "Module GSM / GPRS pour objets connectés : SMS, appels et données, avec antenne.",
     'texte': "Insérez une carte SIM et pilotez le module en commandes AT par son port série pour vos alarmes et capteurs distants.",
     'specs': ["Réseau 2G GSM / GPRS", "SMS, appels et données", "Interface série (UART)", "Antenne fournie"]},

    # ── GSM + GPS ──
    {'nom': 'Module GSM GPRS GPS SIM808 avec antenne GPS', 'prix_source': 15000, 'ref': 'SIM808', 'slug': 'module-gsm-gps-sim808',
     'courte': "GSM + GPS sur une seule carte : le cœur d'un traceur GPS qui envoie sa position par SMS ou par Internet.",
     'texte': "Alimentation 5 à 26 V ou batterie lithium, connecteurs d'antenne SMA et port micro / audio : "
              "suivi de véhicules, de colis ou de troupeaux.",
     'specs': ["Puce SIM808 : GSM / GPRS + GPS", "Alimentation 5 à 26 V ou batterie 3,5 à 4,2 V", "Antennes GSM et GPS sur SMA",
               "Port série TTL", "Antenne GPS fournie"]},
    {'nom': 'Carte A9G GSM GPRS GPS BDS', 'prix_source': 19350, 'ref': 'A9G', 'slug': 'carte-a9g-gsm-gps',
     'courte': "Carte GSM / GPRS avec GPS et Beidou intégrés : pour traceurs et localisation en temps réel.",
     'texte': "Un seul module pour communiquer par le réseau mobile et se localiser par satellite. Port micro USB pour l'alimentation "
              "et la programmation.",
     'specs': ["Module A9G : GSM / GPRS + GPS / BDS", "GSM quadri-bande, GPRS classe 10", "Alimentation 3,4 à 4,2 V ou micro USB"]},

    # ── GPS ──
    {'nom': 'Module GPS NEO-6M', 'prix_source': 2775, 'ref': 'NEO-6M', 'slug': 'module-gps-neo-6m',
     'courte': "Le module GPS le plus utilisé avec Arduino : position, vitesse et heure exacte, avec antenne céramique.",
     'texte': "Il envoie les données de position (trames NMEA) sur son port série. Batterie de sauvegarde pour un démarrage plus rapide.",
     'specs': ["Récepteur GPS u-blox", "Antenne céramique", "Batterie de sauvegarde et LED de signal", "Port série, 9600 bauds",
               "Alimentation 3 à 5 V"]},
    {'nom': 'Module GPS NEO-7M', 'prix_source': 4850, 'ref': 'NEO-7M', 'slug': 'module-gps-neo-7m',
     'courte': "Module GPS NEO-7M (GPS, GLONASS, QZSS, SBAS) avec antenne céramique et batterie de sauvegarde.",
     'texte': "Plus sensible que le NEO-6M, pour la navigation, les traceurs et les drones.",
     'specs': ["GPS / GLONASS / QZSS / SBAS", "Antenne céramique 12 × 12 mm", "Batterie de sauvegarde", "Port série, 9600 bauds",
               "Alimentation 3 à 5 V"]},
    {'nom': 'Module GPS NEO-8M', 'prix_source': 7940, 'ref': 'NEO-8M', 'slug': 'module-gps-neo-8m',
     'courte': "Module GPS multi-constellations (GPS, GLONASS, BeiDou), précision horizontale d'environ 5 m.",
     'texte': "Couverture et précision améliorées grâce à plusieurs systèmes satellites. Compatible avec de nombreux contrôleurs de vol.",
     'specs': ["GPS / GLONASS / BeiDou", "Précision horizontale : environ 5 m", "Antenne céramique", "Horloge temps réel intégrée",
               "Température : -40 à 85 °C"]},
    {'nom': 'Carte GPS GP-02-Kit Ai-Thinker (GPS / BDS / GLONASS)', 'prix_source': 3350, 'ref': 'GP-02', 'slug': 'carte-gps-gp-02-kit',
     'courte': "Carte de positionnement par satellite multi-systèmes (Beidou, GPS, GLONASS), basse consommation.",
     'texte': "Pour les traceurs, le suivi IoT et les services de géolocalisation qui doivent économiser la batterie.",
     'specs': ["Récepteur BDS / GPS / GLONASS", "Processeur RISC 32 bits", "Faible consommation", "Port série"]},
    {'nom': 'Carte GP-01-Kit Ai-Thinker (Wi-Fi 6 + BLE 5.3)', 'prix_source': 3520, 'ref': 'Ai-M61-32S', 'slug': 'carte-gp-01-kit',
     'courte': "Carte multifonction Wi-Fi 6 + Bluetooth LE 5.3 à module Ai-M61-32S, interfaces caméra et écran.",
     'texte': "Processeur RISC-V 320 MHz avec chiffrement matériel, pour l'IoT avancé, la vision embarquée et la domotique.",
     'specs': ["Module Ai-M61-32S, RISC-V jusqu'à 320 MHz", "Wi-Fi 6, Bluetooth LE 5.3, Thread", "Interfaces caméra DVP et écran SPI",
               "USB 2.0, micro SD, Ethernet"]},

    # ── Antennes et câbles ──
    {'nom': 'Antenne LoRa magnétique étanche SMA (433 / 868 / 915 MHz)', 'prix_source': 780, 'ref': 'SMA RG174',
     'slug': 'antenne-lora-magnetique-sma',
     'courte': "Antenne omnidirectionnelle à base aimantée et câble RG174 pour améliorer la portée de vos modules LoRa.",
     'texte': "Se fixe sur une surface métallique, en intérieur ou en extérieur : passerelles LoRaWAN, télémétrie, capteurs distants.",
     'specs': ["Bandes 433 / 868 / 915 MHz (selon modèle)", "Connecteur SMA, câble RG174", "Base magnétique, étanche",
               "Omnidirectionnelle, 50 Ω"]},
    {'nom': 'Mini antenne flexible uFL 15 cm (2,4 / 5 GHz)', 'prix_source': 850, 'ref': 'uFL 2,4 / 5 GHz',
     'slug': 'mini-antenne-flexible-ufl',
     'courte': "Petite antenne adhésive Wi-Fi / Bluetooth double bande avec connecteur uFL (IPEX).",
     'texte': "Améliore la portée des modules à connecteur uFL (ESP32, ESP-12, modules Wi-Fi) placés dans un boîtier.",
     'specs': ["2,4 à 2,5 GHz et 4,9 à 5,9 GHz", "Gain : 4 dBi", "Connecteur uFL (IPEX)", "Câble de 10 cm"]},
    {'nom': 'Câble adaptateur IPEX (uFL) vers RP-SMA femelle', 'prix_source': 450, 'ref': 'uFL → RP-SMA',
     'slug': 'cable-ipex-ufl-rp-sma',
     'courte': "Câble pour relier une antenne RP-SMA à un module à connecteur IPEX (uFL) : Wi-Fi, GPS, LoRa, FPV.",
     'texte': "Permet de sortir l'antenne d'un boîtier et d'utiliser une antenne plus performante.",
     'specs': ["Connecteurs IPEX (uFL) → RP-SMA femelle", "Câble coaxial faible perte", "Connecteur plaqué or"]},
]
