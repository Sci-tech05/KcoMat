"""
Catalogue de formations prérédigées (une par catégorie).

Chargées MASQUÉES : l'admin ajoute l'image, vérifie le tarif et les textes, puis coche « Actif ».
Une formation existante avec le même slug n'est jamais écrasée : seuls ses champs vides sont complétés.
Chargement : bouton « Charger le catalogue » (admin › Formations) ou `python manage.py charger_catalogue_formations`.
"""
from django.db import transaction

MATERIEL_ELECTRONIQUE = [
    "Kit de travaux pratiques prêté pendant toute la formation",
    "Ordinateur de la salle de formation (ou le vôtre)",
    "Supports de cours PDF et fiches de travaux pratiques",
]

CATALOGUE = [
    {
        'slug': 'domotique', 'categorie': 'domotique', 'titre': 'Domotique & IoT',
        'description_courte': "Automatisez éclairage, sécurité et énergie d'une maison : capteurs, modules connectés et pilotage depuis le smartphone.",
        'description': (
            "La domotique regroupe les technologies qui permettent d'automatiser, de contrôler et de coordonner les "
            "équipements d'un logement ou d'un bureau pour gagner en confort, en sécurité et en économies d'énergie.\n\n"
            "En un mois de pratique intensive, vous apprenez à câbler une installation, à paramétrer des modules connectés "
            "et à créer des scénarios pilotés depuis un smartphone. Chaque séance se déroule sur du vrai matériel, "
            "jusqu'à la réalisation d'un projet complet de maison intelligente."
        ),
        'duree': '1 mois', 'niveau': 'debutant', 'prix': 20000, 'prix_avec_base': None, 'places': 20,
        'objectifs': [
            "Comprendre l'architecture d'une installation domotique",
            "Câbler capteurs, relais et actionneurs en toute sécurité",
            "Configurer des modules connectés Wi-Fi et Zigbee",
            "Créer des scénarios d'automatisation (éclairage, alarme, énergie)",
            "Piloter une installation à distance depuis un smartphone",
        ],
        'programme': [
            "Introduction : principes de la domotique, protocoles et usages",
            "Électricité pour la domotique : schémas, protections, câblage sécurisé",
            "Capteurs et actionneurs : mouvement, température, ouverture, relais",
            "Réseau et connectivité : Wi-Fi, Zigbee, passerelles, adresses IP",
            "Automatisations : scénarios, plannings et notifications",
            "Projet final : installation complète d'une maison intelligente",
        ],
        'prerequis': ["Savoir utiliser un smartphone et un ordinateur", "Aucune connaissance en électronique exigée"],
        'public_cible': ["Étudiants et jeunes diplômés", "Électriciens souhaitant se diversifier",
                         "Particuliers et entrepreneurs passionnés de technologie"],
        'debouches': ["Installateur domotique", "Technicien IoT", "Intégrateur de maisons connectées", "Création de son activité d'installation"],
        'materiel': ["Kit domotique (capteurs, relais, modules Wi-Fi/Zigbee) prêté pendant la formation", *MATERIEL_ELECTRONIQUE[1:]],
    },
    {
        'slug': 'electronique-fondamentale', 'categorie': 'electronique', 'titre': 'Électronique fondamentale & Arduino',
        'description_courte': "Des bases de l'électricité jusqu'à vos premiers montages Arduino : comprenez, concevez et dépannez des circuits électroniques.",
        'description': (
            "Cette formation vous donne des bases solides pour comprendre et réaliser des circuits électroniques. "
            "Vous apprenez à lire un schéma, à choisir et à tester les composants, puis à programmer une carte Arduino "
            "pour piloter LED, moteurs et capteurs.\n\n"
            "La pédagogie est 100 % pratique : chaque notion est immédiatement mise en œuvre sur platine d'essai, "
            "avec un mini-projet à la fin de chaque semaine."
        ),
        'duree': '1 mois', 'niveau': 'debutant', 'prix': 20000, 'prix_avec_base': None, 'places': 20,
        'objectifs': [
            "Maîtriser les grandeurs électriques : tension, courant, résistance, puissance",
            "Lire et réaliser un schéma électronique",
            "Identifier, tester et utiliser les composants courants",
            "Mesurer et dépanner avec un multimètre",
            "Programmer une carte Arduino pour piloter des capteurs et actionneurs",
        ],
        'programme': [
            "Les bases : tension, courant, loi d'Ohm, puissance",
            "Composants : résistances, condensateurs, diodes, transistors, circuits intégrés",
            "Mesures : multimètre, alimentation de laboratoire, dépannage",
            "Arduino : environnement, entrées/sorties, premiers programmes",
            "Capteurs et actionneurs : température, lumière, servomoteurs, afficheurs",
            "Projet final : conception d'un système électronique complet",
        ],
        'prerequis': ["Niveau BEPC ou équivalent", "Curiosité et goût pour la manipulation"],
        'public_cible': ["Élèves et étudiants des filières techniques", "Débutants passionnés d'électronique",
                         "Réparateurs souhaitant consolider leurs bases"],
        'debouches': ["Technicien en électronique", "Réparateur d'équipements électroniques", "Poursuite vers l'IoT et l'embarqué"],
        'materiel': ["Kit Arduino complet (carte, platine, composants, capteurs) prêté pendant la formation", *MATERIEL_ELECTRONIQUE[1:]],
    },
    {
        'slug': 'micropython-esp32', 'categorie': 'micropython', 'titre': 'MicroPython & ESP32 : objets connectés',
        'description_courte': "Programmez des objets connectés en MicroPython sur ESP32 : capteurs, Wi-Fi, MQTT et tableaux de bord en temps réel.",
        'description': (
            "MicroPython permet de programmer des microcontrôleurs avec la simplicité du langage Python. Sur une carte ESP32, "
            "vous créez des objets connectés capables de mesurer, de communiquer en Wi-Fi et d'envoyer leurs données vers "
            "un tableau de bord.\n\n"
            "Cette formation est idéale après la formation Domotique : les anciens apprenants bénéficient d'un tarif réduit."
        ),
        'duree': '1 mois', 'niveau': 'intermediaire', 'prix': 25000, 'prix_avec_base': 15000, 'places': 20,
        'objectifs': [
            "Programmer un ESP32 en MicroPython",
            "Lire des capteurs et commander des actionneurs",
            "Connecter un objet au Wi-Fi et à Internet",
            "Échanger des données avec le protocole MQTT",
            "Créer un tableau de bord de supervision en temps réel",
        ],
        'programme': [
            "Python essentiel : variables, conditions, boucles, fonctions",
            "ESP32 et MicroPython : installation, REPL, broches GPIO",
            "Capteurs et actionneurs : I2C, PWM, conversion analogique",
            "Connectivité : Wi-Fi, requêtes HTTP, serveur web embarqué",
            "IoT : protocole MQTT, tableau de bord, alertes",
            "Projet final : station connectée (météo, énergie ou sécurité)",
        ],
        'prerequis': ["Bases en électronique (formation Domotique ou Électronique recommandée)", "Savoir utiliser un ordinateur"],
        'public_cible': ["Anciens apprenants Domotique et Électronique", "Étudiants en informatique ou électronique",
                         "Makers et porteurs de projets IoT"],
        'debouches': ["Développeur IoT", "Technicien en systèmes embarqués", "Prototypage de produits connectés"],
        'materiel': ["Carte ESP32 et kit de capteurs prêtés pendant la formation", *MATERIEL_ELECTRONIQUE[1:]],
    },
    {
        'slug': 'developpement-web-mobile', 'categorie': 'programme-web-mobile', 'titre': 'Développement Web & Mobile',
        'description_courte': "Créez des sites et des applications web modernes, de la maquette à la mise en ligne, avec paiement Mobile Money.",
        'description': (
            "Apprenez à concevoir et à développer des sites web et des applications complètes : pages modernes et "
            "responsives, base de données, comptes utilisateurs, paiement Mobile Money et mise en ligne.\n\n"
            "Vous travaillez sur un projet personnel tout au long de la formation et repartez avec une réalisation "
            "concrète à présenter dans votre portfolio."
        ),
        'duree': '2 mois', 'niveau': 'debutant', 'prix': 35000, 'prix_avec_base': None, 'places': 15,
        'objectifs': [
            "Créer des pages web modernes et adaptées au mobile (HTML, CSS, JavaScript)",
            "Développer une application web avec Python et Django",
            "Concevoir et utiliser une base de données",
            "Intégrer un paiement Mobile Money",
            "Mettre un site en ligne et le maintenir",
        ],
        'programme': [
            "Fondamentaux du web : HTML, CSS, design responsive",
            "JavaScript : interactions, formulaires, appels d'API",
            "Python & Django : pages, modèles, administration",
            "Bases de données : conception, requêtes, sécurité",
            "Fonctionnalités avancées : comptes, paiement Mobile Money, e-mails",
            "Mise en production : hébergement, nom de domaine, Git",
        ],
        'prerequis': ["Savoir utiliser un ordinateur", "Disposer idéalement d'un ordinateur personnel"],
        'public_cible': ["Étudiants et jeunes diplômés", "Entrepreneurs souhaitant créer leur site",
                         "Personnes en reconversion vers le numérique"],
        'debouches': ["Développeur web", "Développeur freelance", "Création de sites pour entreprises et commerces"],
        'materiel': ["Ordinateur de la salle de formation (ou le vôtre)", "Hébergement de démonstration pour votre projet",
                     "Supports de cours PDF et exercices corrigés"],
    },
    {
        'slug': 'electricite-batiment', 'categorie': 'electricite-batiment', 'titre': 'Électricité bâtiment',
        'description_courte': "Réalisez des installations électriques domestiques sûres et conformes : schémas, câblage, tableaux et dépannage.",
        'description': (
            "Cette formation vous apprend à réaliser une installation électrique domestique complète, de la lecture du "
            "plan à la mise en service, en respectant les normes et les règles de sécurité.\n\n"
            "Les travaux pratiques se déroulent sur des panneaux de câblage reproduisant de vraies situations de chantier."
        ),
        'duree': '1 mois', 'niveau': 'debutant', 'prix': 25000, 'prix_avec_base': None, 'places': 20,
        'objectifs': [
            "Lire et réaliser les schémas d'une installation domestique",
            "Câbler les circuits d'éclairage et de prises",
            "Réaliser et raccorder un tableau électrique",
            "Choisir les protections adaptées (disjoncteurs, différentiels)",
            "Diagnostiquer et réparer les pannes courantes",
        ],
        'programme': [
            "Sécurité électrique : risques, équipements de protection, consignation",
            "Schémas : symboles, plans, schémas développés et architecturaux",
            "Circuits : simple allumage, va-et-vient, télérupteur, prises",
            "Tableau électrique : protections, repérage, raccordement",
            "Normes et mesures : mise à la terre, contrôles, mise en service",
            "Dépannage : méthodes de diagnostic et cas pratiques",
        ],
        'prerequis': ["Aucun prérequis technique", "Bonne condition physique pour les travaux pratiques"],
        'public_cible': ["Jeunes souhaitant apprendre un métier", "Aides-électriciens voulant se perfectionner",
                         "Propriétaires et gestionnaires de bâtiments"],
        'debouches': ["Électricien bâtiment", "Technicien de maintenance", "Installateur indépendant"],
        'materiel': ["Panneaux de câblage et outillage d'électricien fournis", "Équipements de protection individuelle",
                     "Supports de cours PDF"],
    },
    {
        'slug': 'electricite-industrielle-automatisme', 'categorie': 'electricite-industrielle', 'titre': 'Électricité industrielle & automatisme',
        'description_courte': "Moteurs, variateurs, armoires de commande et automates programmables : maîtrisez l'électricité des machines industrielles.",
        'description': (
            "Entrez dans le monde de l'industrie : commande des moteurs, armoires électriques, variateurs de vitesse et "
            "programmation d'automates. Vous apprenez à câbler, à programmer et à dépanner les équipements que l'on "
            "trouve dans les usines, les unités de transformation et les exploitations agricoles."
        ),
        'duree': '2 mois', 'niveau': 'intermediaire', 'prix': 35000, 'prix_avec_base': None, 'places': 15,
        'objectifs': [
            "Lire les schémas de puissance et de commande",
            "Câbler le démarrage et la protection des moteurs",
            "Paramétrer un variateur de vitesse",
            "Programmer un automate en langage Ladder",
            "Diagnostiquer une panne sur une machine",
        ],
        'programme': [
            "Schémas industriels : puissance, commande, repérage",
            "Moteurs : démarrage direct, étoile-triangle, inversion de sens",
            "Protections : disjoncteurs moteur, relais thermiques, sécurités",
            "Variateurs de vitesse : principe, paramétrage, mise en service",
            "Automates programmables : Ladder, temporisations, compteurs",
            "Maintenance : diagnostic, méthodes et cas pratiques",
        ],
        'prerequis': ["Bases en électricité (formation Électricité bâtiment ou équivalent)"],
        'public_cible': ["Électriciens souhaitant évoluer vers l'industrie", "Étudiants en électrotechnique",
                         "Techniciens de maintenance"],
        'debouches': ["Électricien industriel", "Technicien de maintenance industrielle", "Automaticien"],
        'materiel': ["Platines de câblage, moteurs et automates de démonstration", "Outillage et équipements de protection",
                     "Supports de cours PDF"],
    },
    {
        'slug': 'intelligence-artificielle-appliquee', 'categorie': 'intelligence-artificielle-appliquee', 'titre': 'Intelligence artificielle appliquée',
        'description_courte': "Comprenez et utilisez l'IA : Python, données, apprentissage automatique et vision par ordinateur sur des cas concrets.",
        'description': (
            "Démystifiez l'intelligence artificielle et apprenez à l'appliquer à des problèmes concrets : analyse de "
            "données, prédiction, reconnaissance d'images et IA embarquée sur de petites cartes électroniques.\n\n"
            "La formation privilégie des cas d'usage africains : agriculture, santé, commerce et énergie."
        ),
        'duree': '2 mois', 'niveau': 'intermediaire', 'prix': 40000, 'prix_avec_base': None, 'places': 15,
        'objectifs': [
            "Programmer en Python pour la donnée",
            "Préparer, analyser et visualiser un jeu de données",
            "Entraîner et évaluer des modèles d'apprentissage automatique",
            "Réaliser un projet de vision par ordinateur",
            "Utiliser les outils d'IA générative de façon responsable",
        ],
        'programme': [
            "Python pour la donnée : pandas, NumPy, visualisation",
            "Apprentissage automatique : régression, classification, évaluation",
            "Réseaux de neurones : principes et premiers modèles",
            "Vision par ordinateur : détection et reconnaissance d'images",
            "IA embarquée : modèles légers sur cartes électroniques",
            "Projet final : une solution d'IA pour un cas réel",
        ],
        'prerequis': ["Bases en programmation (idéalement Python)", "Niveau mathématique de terminale"],
        'public_cible': ["Étudiants en informatique, mathématiques ou statistiques", "Développeurs souhaitant se spécialiser",
                         "Chercheurs et porteurs de projets innovants"],
        'debouches': ["Data analyst", "Développeur IA", "Ingénieur en vision par ordinateur"],
        'materiel': ["Ordinateur de la salle de formation (ou le vôtre)", "Accès à des environnements de calcul en ligne",
                     "Jeux de données et notebooks d'exercices"],
    },
    {
        'slug': 'pilotage-de-drone', 'categorie': 'pilotage-de-drone', 'titre': 'Pilotage de drone',
        'description_courte': "Apprenez à piloter un drone en toute sécurité : vol manuel, missions photo et vidéo, réglementation et entretien.",
        'description': (
            "Cette formation vous apprend à piloter un drone avec précision et en toute sécurité. Vous commencez sur "
            "simulateur, puis vous progressez en vol réel jusqu'à la réalisation de missions de prise de vue aérienne.\n\n"
            "Vous apprenez aussi les règles de sécurité, la préparation des missions et l'entretien de l'appareil."
        ),
        'duree': '2 semaines', 'niveau': 'debutant', 'prix': 30000, 'prix_avec_base': None, 'places': 10,
        'objectifs': [
            "Connaître les règles de sécurité et la réglementation",
            "Préparer une mission : météo, zone, plan de vol, checklists",
            "Maîtriser le vol manuel et les modes automatiques",
            "Réaliser des prises de vue photo et vidéo aériennes",
            "Entretenir son drone et ses batteries",
        ],
        'programme': [
            "Sécurité et réglementation : règles de vol, zones, responsabilités",
            "Simulateur : prise en main des commandes",
            "Vol réel : décollage, vol stationnaire, trajectoires, atterrissage",
            "Prise de vue : cadrage, réglages caméra, mouvements cinématiques",
            "Missions : planification, vol automatique, gestion des imprévus",
            "Entretien : batteries, hélices, mises à jour",
        ],
        'prerequis': ["Avoir 16 ans minimum", "Aucune expérience de pilotage exigée"],
        'public_cible': ["Photographes et vidéastes", "Professionnels de l'agriculture, du BTP et de l'immobilier",
                         "Passionnés d'aéronautique"],
        'debouches': ["Télépilote de drone", "Prestataire de prises de vue aériennes", "Opérateur drone pour l'agriculture"],
        'materiel': ["Drone d'entraînement et simulateur fournis", "Batteries et équipements de sécurité", "Supports de cours PDF"],
    },
    {
        'slug': 'conception-pilotage-de-drone', 'categorie': 'conception-pilotage-de-drone', 'titre': 'Conception & pilotage de drone',
        'description_courte': "Construisez votre propre drone de A à Z : châssis, moteurs, électronique de vol, réglages et premiers vols.",
        'description': (
            "Allez plus loin que le pilotage : concevez, assemblez et réglez votre propre drone. Vous apprenez le rôle de "
            "chaque composant, la soudure, la configuration du contrôleur de vol et les réglages, avant de piloter "
            "l'appareil que vous avez construit.\n\n"
            "Une formation complète pour celles et ceux qui veulent maîtriser la technologie des drones de bout en bout."
        ),
        'duree': '2 mois', 'niveau': 'avance', 'prix': 50000, 'prix_avec_base': None, 'places': 10,
        'objectifs': [
            "Comprendre le fonctionnement complet d'un drone",
            "Choisir et dimensionner les composants (moteurs, hélices, batteries)",
            "Assembler et souder l'électronique de vol",
            "Configurer et régler le contrôleur de vol",
            "Piloter et faire évoluer son propre drone",
        ],
        'programme': [
            "Principes du vol : aérodynamique, forces, types de drones",
            "Composants : châssis, moteurs, contrôleurs, hélices, batteries",
            "Électronique : soudure, câblage, radio et télémétrie",
            "Contrôleur de vol : configuration, calibrage, modes de vol",
            "Réglages et essais : stabilité, sécurité, premiers vols",
            "Pilotage et missions : vol manuel, vol automatique, applications",
        ],
        'prerequis': ["Bases en électronique recommandées", "Avoir 16 ans minimum"],
        'public_cible': ["Étudiants en électronique, mécanique ou aéronautique", "Makers et passionnés de drones",
                         "Télépilotes souhaitant maîtriser la technique"],
        'debouches': ["Technicien drone", "Télépilote professionnel", "Création d'une activité de services par drone"],
        'materiel': ["Kit de construction de drone et outillage de soudure fournis", "Simulateur de vol", "Supports de cours PDF"],
    },
    {
        'slug': 'securite-informatique', 'categorie': 'securite-informatique', 'titre': 'Sécurité informatique & réseaux',
        'description_courte': "Protégez ordinateurs, réseaux et données : configuration réseau, bonnes pratiques, tests de sécurité et réaction aux incidents.",
        'description': (
            "Les cyberattaques touchent aussi bien les particuliers que les entreprises et les administrations. Cette "
            "formation vous apprend à comprendre les menaces, à sécuriser un réseau et des postes de travail, et à réagir "
            "en cas d'incident.\n\n"
            "Les travaux pratiques se déroulent dans un laboratoire isolé, dans un cadre légal et éthique."
        ),
        'duree': '1 mois', 'niveau': 'intermediaire', 'prix': 35000, 'prix_avec_base': None, 'places': 15,
        'objectifs': [
            "Comprendre les principales menaces et attaques",
            "Configurer et sécuriser un réseau local",
            "Sécuriser postes de travail, comptes et sauvegardes",
            "Réaliser des tests de sécurité dans un cadre légal",
            "Réagir à un incident et sensibiliser les utilisateurs",
        ],
        'programme': [
            "Menaces : hameçonnage, logiciels malveillants, intrusions",
            "Réseaux : TCP/IP, routage, Wi-Fi, segmentation",
            "Protection : pare-feu, antivirus, mots de passe, chiffrement",
            "Tests de sécurité : audit, outils, éthique et cadre légal",
            "Sauvegardes et continuité : plans de reprise après incident",
            "Réponse aux incidents et sensibilisation des utilisateurs",
        ],
        'prerequis': ["Bonne maîtrise de l'ordinateur", "Notions de réseau appréciées"],
        'public_cible': ["Techniciens et administrateurs informatiques", "Étudiants en informatique et réseaux",
                         "Responsables informatiques de PME et d'institutions"],
        'debouches': ["Technicien réseaux et sécurité", "Administrateur systèmes", "Consultant en cybersécurité junior"],
        'materiel': ["Laboratoire de tests isolé", "Ordinateur de la salle de formation (ou le vôtre)", "Supports de cours PDF"],
    },
]


def _valeurs(fiche):
    return {
        'titre': fiche['titre'],
        'description_courte': fiche['description_courte'],
        'description': fiche['description'],
        'duree': fiche['duree'],
        'niveau': fiche['niveau'],
        'prix': fiche['prix'],
        'prix_avec_base': fiche['prix_avec_base'],
        'places_disponibles': fiche['places'],
        'objectifs': '\n'.join(fiche['objectifs']),
        'programme': '\n'.join(fiche['programme']),
        'prerequis': '\n'.join(fiche['prerequis']),
        'public_cible': '\n'.join(fiche['public_cible']),
        'debouches': '\n'.join(fiche['debouches']),
        'materiel_fourni': '\n'.join(fiche['materiel']),
    }


CHAMPS_TEXTE = ('objectifs', 'programme', 'prerequis', 'public_cible', 'debouches', 'materiel_fourni')


@transaction.atomic
def charger_catalogue(force=False):
    """
    Crée les formations absentes (masquées, sans image, marquées « Nouveau »).
    Formation déjà présente (même slug) : seuls ses champs texte VIDES sont complétés ;
    force=True réécrit tous les textes du catalogue (jamais l'image, le statut ni les sessions).
    Retourne (créées, complétées, inchangées).
    """
    from .models import CategorieFormation, Formation

    crees = completees = inchangees = 0
    for fiche in CATALOGUE:
        categorie = CategorieFormation.objects.filter(slug=fiche['categorie']).first()
        valeurs = _valeurs(fiche)
        formation = Formation.objects.filter(slug=fiche['slug']).first()
        if formation is None:
            Formation.objects.create(slug=fiche['slug'], categorie=categorie, actif=False, nouveau=True, **valeurs)
            crees += 1
            continue
        champs = valeurs if force else {c: valeurs[c] for c in CHAMPS_TEXTE if not (getattr(formation, c) or '').strip()}
        if champs:
            Formation.objects.filter(pk=formation.pk).update(**champs)   # update() : pas de notification push
            completees += 1
        else:
            inchangees += 1
    return crees, completees, inchangees
