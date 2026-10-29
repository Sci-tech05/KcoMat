"""Webinaires proposés, chargés masqués depuis l'admin (« Charger les webinaires proposés »).

Les dates sont une proposition : un samedi sur deux de 20 h 00 à 22 h 00, à partir du samedi suivant.
Un webinaire déjà présent (même slug) n'est jamais modifié.
"""
from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Webinaire

# Horaire de tous les webinaires (heure du Bénin)
HEURE_DEBUT = time(20, 0)
HEURE_FIN = time(22, 0)

CATALOGUE = [
    {
        'slug': 'introduction-aux-systemes-embarques-arduino-esp32',
        'titre': "Introduction aux systèmes embarqués : de l'Arduino à l'ESP32",
        'theme': 'embarque',
        'accroche': "Comprendre ce qui se cache dans une carte électronique programmable, et choisir la bonne pour son projet.",
        'description': (
            "Un système embarqué, c'est un petit ordinateur dédié à une seule mission : piloter un portail, "
            "mesurer la température d'une chambre froide, compter des visiteurs… Ils sont partout autour de nous, "
            "et il n'a jamais été aussi simple d'en concevoir un.\n\n"
            "Pendant ce webinaire, nous partons de l'Arduino Uno, la carte idéale pour débuter, pour arriver à "
            "l'ESP32, qui ajoute le Wi-Fi, le Bluetooth et beaucoup plus de puissance pour un prix très proche. "
            "Démonstrations en direct, schémas commentés et temps de questions-réponses à la fin."
        ),
        'points_cles': (
            "Ce qu'est un microcontrôleur et comment il exécute un programme\n"
            "Entrées, sorties, capteurs et actionneurs : le vocabulaire indispensable\n"
            "Arduino Uno, Nano, ESP8266, ESP32 : forces, limites et prix au Bénin\n"
            "Démonstration : du premier clignotement de LED à une mesure affichée sur téléphone\n"
            "Le matériel minimal pour commencer chez soi"
        ),
    },
    {
        'slug': 'iot-connecter-un-capteur-au-cloud-avec-esp32',
        'titre': "IoT concret : connecter un capteur au cloud avec l'ESP32",
        'theme': 'iot',
        'accroche': "Des mesures prises par un capteur, envoyées sur internet et consultées en temps réel depuis un téléphone.",
        'description': (
            "L'Internet des objets n'est pas réservé aux grandes entreprises. Avec une carte ESP32 et un capteur "
            "à quelques milliers de francs, on peut surveiller à distance une serre, un réservoir d'eau ou une "
            "salle serveur.\n\n"
            "Nous construisons ensemble, en direct, une chaîne complète : lecture d'un capteur de température "
            "et d'humidité, envoi des données par Wi-Fi avec le protocole MQTT, stockage dans le cloud et "
            "tableau de bord consultable partout. Vous repartez avec une architecture que vous pourrez reproduire."
        ),
        'points_cles': (
            "L'architecture d'un objet connecté : capteur, passerelle, cloud, application\n"
            "Lire un capteur DHT22 ou BME280 avec l'ESP32\n"
            "Envoyer ses données avec MQTT : courtier, sujets, qualité de service\n"
            "Créer un tableau de bord et recevoir une alerte sur son téléphone\n"
            "Consommation, coupures réseau, sécurité : les pièges du terrain"
        ),
    },
    {
        'slug': 'edge-ai-intelligence-artificielle-sur-microcontroleur',
        'titre': "Edge AI : faire tourner l'intelligence artificielle sur un microcontrôleur",
        'theme': 'ia',
        'accroche': "Reconnaître un son, un geste ou une image directement sur une petite carte, sans connexion internet.",
        'description': (
            "L'intelligence artificielle ne vit pas seulement dans d'énormes centres de données. Grâce au TinyML, "
            "un modèle peut tenir dans quelques centaines de kilo-octets et fonctionner sur une carte alimentée "
            "par une simple batterie.\n\n"
            "Ce webinaire démystifie l'IA embarquée : collecte des données, entraînement d'un modèle, "
            "compression puis déploiement sur un microcontrôleur. Nous montrons en direct un exemple de "
            "reconnaissance de mots-clés et discutons des applications utiles en Afrique : agriculture, santé, sécurité."
        ),
        'points_cles': (
            "Pourquoi exécuter l'IA sur l'appareil plutôt que dans le cloud\n"
            "Le cycle complet : données, entraînement, quantification, déploiement\n"
            "Outils accessibles : Edge Impulse, TensorFlow Lite Micro\n"
            "Démonstration : reconnaissance vocale de mots-clés sur ESP32\n"
            "Idées de projets à fort impact local"
        ),
    },
    {
        'slug': 'python-pour-l-electronique-et-l-automatisation',
        'titre': "Python pour l'électronique et l'automatisation",
        'theme': 'python',
        'accroche': "Le langage le plus apprécié des débutants, appliqué aux cartes électroniques et aux tâches répétitives.",
        'description': (
            "Python est lisible, polyvalent et omniprésent. Il permet aussi de programmer des cartes "
            "électroniques grâce à MicroPython, de piloter un Raspberry Pi ou d'automatiser des tâches qui "
            "vous prennent des heures chaque semaine.\n\n"
            "Nous verrons comment un même langage relie le monde physique et l'ordinateur : allumer une sortie, "
            "lire un capteur, enregistrer des mesures dans un fichier Excel et générer un rapport automatiquement. "
            "Aucun prérequis en programmation n'est nécessaire pour suivre."
        ),
        'points_cles': (
            "Les bases de Python expliquées simplement\n"
            "MicroPython sur ESP32 : programmer une carte sans compilateur\n"
            "Raspberry Pi : commander des relais et des capteurs depuis Python\n"
            "Automatiser : fichiers, tableurs, e-mails et rapports\n"
            "Le parcours pour progresser après le webinaire"
        ),
    },
    {
        'slug': 'domotique-a-petit-budget-automatiser-sa-maison',
        'titre': "Domotique à petit budget : automatiser sa maison dès la construction",
        'theme': 'domotique',
        'accroche': "Les bons choix à faire pendant le chantier pour une maison intelligente, économe et évolutive.",
        'description': (
            "Éclairage commandé depuis le téléphone, portail automatique, surveillance des consommations, "
            "alertes en cas d'intrusion : la domotique coûte beaucoup moins cher lorsqu'elle est prévue dès la "
            "construction, au moment où l'on pose les gaines et le tableau électrique.\n\n"
            "Ce webinaire s'adresse aux particuliers, électriciens et maîtres d'ouvrage. Nous présentons les "
            "équipements fiables et disponibles localement, une méthode pour chiffrer son projet et les "
            "erreurs de câblage qui empêchent d'automatiser plus tard."
        ),
        'points_cles': (
            "Ce qu'il faut prévoir dès le gros œuvre : gaines, boîtiers, tableau\n"
            "Filaire ou sans fil : comparer coûts, fiabilité et maintenance\n"
            "Éclairage, prises, portail, sécurité : les automatisations les plus rentables\n"
            "Énergie solaire et suivi des consommations\n"
            "Exemple de budget pour une villa de 3 chambres"
        ),
    },
    {
        'slug': 'lancer-son-projet-tech-du-prototype-au-produit',
        'titre': "Lancer son projet tech : du prototype au produit",
        'theme': 'entrepreneuriat',
        'accroche': "Transformer une idée qui fonctionne sur la table du salon en un produit que l'on peut vendre.",
        'description': (
            "Beaucoup de projets techniques s'arrêtent au stade du prototype. Passer au produit demande de "
            "valider son marché, de fiabiliser la conception, de maîtriser ses coûts et de trouver les bons "
            "partenaires.\n\n"
            "À partir de projets réalisés par KcoMat et ses apprenants, nous détaillons les étapes concrètes "
            "et les outils pour avancer sans brûler son budget : preuve de concept, circuit imprimé, boîtier, "
            "premières ventes, financement et protection de son travail."
        ),
        'points_cles': (
            "Valider son idée auprès de vrais utilisateurs avant d'investir\n"
            "Du montage sur plaque d'essai au circuit imprimé et au boîtier\n"
            "Calculer son coût de revient et fixer son prix\n"
            "Financements, incubateurs et concours accessibles au Bénin\n"
            "Retour d'expérience sur des projets KcoMat"
        ),
    },
    {
        'slug': 'robotique-mobile-pour-debutants',
        'titre': "Robotique mobile pour débutants",
        'theme': 'robotique',
        'accroche': "Faire avancer, tourner et éviter les obstacles à un petit robot, en comprenant chaque étape.",
        'description': (
            "Un robot mobile réunit tout ce qui rend l'électronique passionnante : mécanique, moteurs, "
            "capteurs et programmation. C'est aussi un excellent support pour initier des élèves ou des "
            "étudiants à la technologie.\n\n"
            "Nous assemblons virtuellement un robot à deux roues : choix du châssis et des moteurs, commande "
            "avec un pont en H, détection d'obstacles par ultrasons et suivi de ligne. Démonstration en vidéo "
            "et liste complète du matériel pour le reproduire."
        ),
        'points_cles': (
            "Les éléments d'un robot : châssis, moteurs, alimentation, cerveau\n"
            "Piloter des moteurs à courant continu avec un driver L298N\n"
            "Éviter les obstacles avec un capteur à ultrasons\n"
            "Suivre une ligne avec des capteurs infrarouges\n"
            "Pistes pour aller plus loin : Bluetooth, caméra, compétitions"
        ),
    },
    {
        'slug': 'comprendre-l-algorithme-et-la-programmation',
        'titre': "Comprendre l'Algorithme & la Programmation",
        'theme': 'algorithmique',
        'accroche': "Apprendre à penser comme un programmeur : découper un problème, l'écrire en étapes, puis le traduire en code.",
        'description': (
            "Avant d'écrire la moindre ligne de code, un bon programmeur sait décrire précisément ce que la machine "
            "doit faire. C'est le rôle de l'algorithme : une suite d'instructions claires qui mène d'un problème "
            "à sa solution, comme une recette de cuisine.\n\n"
            "Ce webinaire pose des bases solides, sans prérequis : variables, conditions, boucles et fonctions, "
            "expliquées avec des exemples du quotidien puis traduites en pseudo-code et en Python. Nous résolvons "
            "ensemble de petits exercices en direct, et vous repartez avec une méthode pour aborder n'importe quel "
            "langage, ainsi que la programmation des cartes électroniques."
        ),
        'points_cles': (
            "Ce qu'est un algorithme et pourquoi il vient avant le code\n"
            "Variables, conditions et boucles : les briques de tout programme\n"
            "Écrire un algorithme en pseudo-code puis le représenter en organigramme\n"
            "Passer du pseudo-code au langage Python, pas à pas\n"
            "Méthode pour résoudre un problème : découper, tester, corriger\n"
            "Les ressources pour continuer à progresser seul"
        ),
    },
]


def calendrier_propose(maintenant=None, nombre=len(CATALOGUE)):
    """Un samedi sur deux, de HEURE_DEBUT à HEURE_FIN, à partir du prochain samedi (heure locale)."""
    aujourd_hui = timezone.localtime(maintenant or timezone.now()).date()
    samedi = aujourd_hui + timedelta(days=(5 - aujourd_hui.weekday()) % 7 or 7)
    zone = timezone.get_current_timezone()
    for i in range(nombre):
        jour = samedi + timedelta(weeks=2 * i)
        yield (timezone.make_aware(datetime.combine(jour, HEURE_DEBUT), zone),
               timezone.make_aware(datetime.combine(jour, HEURE_FIN), zone))


def charger_catalogue():
    """Crée les webinaires manquants (masqués). Renvoie (créés, déjà présents)."""
    crees = presents = 0
    for donnees, (debut, fin) in zip(CATALOGUE, calendrier_propose()):
        if Webinaire.objects.filter(slug=donnees['slug']).exists():
            presents += 1
            continue
        Webinaire.objects.create(**donnees, date_debut=debut, date_fin=fin, actif=False)
        crees += 1
    return crees, presents
