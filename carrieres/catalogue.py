"""
Catalogue d'offres prérédigées (une par catégorie × domaine).

Chargées MASQUÉES : l'admin ajoute l'image, ajuste si besoin, puis coche « Publiée ».
Chargement : bouton « Charger le catalogue » dans l'admin des offres, ou
`python manage.py charger_catalogue_offres`.
"""
from django.db import transaction

AVANTAGES = {
    'stage': [
        "Encadrement par un professionnel référent tout au long du stage",
        "Pratique sur du vrai matériel et des projets clients réels",
        "Attestation de stage KcoMat en fin de parcours",
        "Accès aux ressources et aux formations internes de KcoMat",
        "Possibilité d'embauche ou de missions pour les meilleurs profils",
    ],
    'emploi': [
        "Contrat de travail et rémunération selon le profil",
        "Projets variés et responsabilités réelles dès l'arrivée",
        "Formation continue sur les nouvelles technologies",
        "Équipe jeune, dynamique et passionnée",
        "Perspectives d'évolution au sein de KcoMat",
    ],
    'freelance': [
        "Missions définies à l'avance (périmètre, durée, livrables)",
        "Rémunération par mission, payée par Mobile Money ou virement",
        "Flexibilité : vous choisissez les missions qui vous conviennent",
        "Collaboration régulière avec une équipe technique reconnue",
    ],
}

PROFIL_TYPE = {
    'stage': "Étudiant(e) ou jeune diplômé(e), motivé(e) à apprendre sur le terrain",
    'emploi': "Expérience professionnelle réussie dans un poste similaire",
    'freelance': "Statut d'indépendant (ou disposé(e) à l'obtenir) et disponibilité ponctuelle",
}

FORMULES_STAGE = [
    {'duree': '1 mois', 'montant': 20000, 'description': 'Découverte du métier et premières réalisations',
     'recommandee': False, 'ordre': 1},
    {'duree': '3 mois et plus', 'montant': 50000, 'description': 'Immersion complète et projet encadré de bout en bout',
     'recommandee': True, 'ordre': 2},
]

REGLAGES_TYPE = {
    'stage': {'nature_montant': 'frais', 'remuneration': '', 'places': 3},
    'emploi': {'nature_montant': 'remuneration', 'remuneration': 'Selon profil et expérience', 'places': 1},
    'freelance': {'nature_montant': 'remuneration', 'remuneration': 'Rémunération par mission', 'places': None},
}

DOMAINES = {
    'domotique': {
        'competences': [
            "Électricité : lecture de schémas, câblage d'armoires et respect des normes (NF C 15-100)",
            "Informatique : configuration de réseaux IP (adressage, Wi-Fi) et bases en programmation",
            "Protocoles : notions sur KNX, Zigbee, MQTT, Arduino, Raspberry Pi ou équivalents",
            "Savoir-être : rigueur technique, curiosité pour les objets connectés et bon relationnel",
        ],
        'profil': [
            "Passionné(e) par les objets connectés et l'automatisation",
            "Soigneux(se) et attentif(ve) à la sécurité électrique",
            "À l'aise avec les clients et les explications simples",
        ],
        'stage': {
            'titre': "Stagiaire technicien(ne) domotique & IoT",
            'accroche': "Participez à l'installation de maisons intelligentes : capteurs, automatismes et pilotage à distance.",
            'description': "Au sein de notre équipe technique, vous participez au déploiement et à la maintenance de solutions domotiques et connectées chez nos clients particuliers et professionnels. Encadré(e) par un technicien référent, vous découvrez toute la chaîne d'un projet : de l'étude du besoin à la mise en service.",
            'missions': [
                "Assister le technicien référent dans le câblage et l'installation des équipements",
                "Paramétrer capteurs, modules connectés et passerelles IoT",
                "Configurer les réseaux Wi-Fi et les applications de pilotage à distance",
                "Participer aux tests, à la mise en service et à la prise en main par les clients",
                "Rédiger les comptes rendus d'intervention",
            ],
            'niveau': "BTS, DUT ou Licence en électrotechnique, électronique ou informatique (en cours ou obtenu)",
        },
        'emploi': {
            'titre': "Technicien(ne) domotique & IoT",
            'accroche': "Prenez en charge nos projets de maisons et bureaux intelligents, de l'étude à la mise en service.",
            'description': "Vous rejoignez l'équipe technique de KcoMat pour concevoir, installer et maintenir des solutions domotiques et connectées. Interlocuteur technique des clients sur le terrain, vous garantissez des installations fiables, sûres et faciles à utiliser.",
            'missions': [
                "Analyser le besoin du client et proposer une solution adaptée (éclairage, sécurité, énergie, confort)",
                "Réaliser le câblage, l'installation et le paramétrage des équipements",
                "Programmer les scénarios d'automatisation et les tableaux de bord",
                "Assurer la maintenance préventive et le dépannage",
                "Encadrer les stagiaires lors des interventions",
            ],
            'niveau': "BTS / Licence en électrotechnique ou électronique, 1 à 2 ans d'expérience",
        },
        'freelance': {
            'titre': "Freelance – Intégrateur(trice) domotique",
            'accroche': "Renforcez nos équipes sur des chantiers domotiques ponctuels, partout au Bénin.",
            'description': "KcoMat fait appel à des intégrateurs indépendants pour accompagner ses pics d'activité : installation de kits domotiques, paramétrage de passerelles et mise en service chez les clients. Chaque mission est définie à l'avance (cahier des charges, durée, livrables).",
            'missions': [
                "Installer et paramétrer des kits domotiques selon le cahier des charges",
                "Mettre en service les automatismes et vérifier leur bon fonctionnement",
                "Former le client à l'utilisation de son installation",
                "Remettre un rapport d'intervention avec photos",
            ],
            'niveau': "Expérience confirmée en installation domotique",
        },
    },
    'electricite_batiment': {
        'competences': [
            "Électricité : lecture de plans, dimensionnement des circuits et des protections",
            "Normes : connaissance de la NF C 15-100 et des règles de sécurité (habilitation appréciée)",
            "Outillage : maîtrise du multimètre, du testeur d'isolement et de l'outillage de chantier",
            "Savoir-être : ponctualité, sens du travail soigné et esprit d'équipe",
        ],
        'profil': [
            "Rigoureux(se) et soucieux(se) de la sécurité",
            "Bonne condition physique pour le travail de chantier",
            "Autonome dans l'organisation de son travail",
        ],
        'stage': {
            'titre': "Stagiaire électricien(ne) bâtiment",
            'accroche': "Apprenez le métier sur de vrais chantiers : installations neuves, rénovations et mises aux normes.",
            'description': "Intégré(e) à nos équipes d'installation, vous intervenez sur des chantiers résidentiels et tertiaires. Aux côtés d'électriciens expérimentés, vous apprenez à lire un plan, à réaliser une installation conforme et à appliquer les règles de sécurité.",
            'missions': [
                "Participer à la préparation des chantiers (matériel, plans, métrés)",
                "Réaliser les saignées, la pose des gaines et le tirage des câbles",
                "Câbler les tableaux de répartition et les appareillages",
                "Participer aux contrôles de continuité, d'isolement et de fonctionnement",
                "Respecter les consignes de sécurité et la propreté du chantier",
            ],
            'niveau': "CAP, Bac pro, BT ou BTS en électricité / électrotechnique",
        },
        'emploi': {
            'titre': "Électricien(ne) bâtiment confirmé(e)",
            'accroche': "Réalisez des installations électriques fiables et conformes pour nos clients particuliers et professionnels.",
            'description': "Vous prenez en charge des chantiers d'installation et de rénovation électrique, de la lecture des plans à la réception des travaux. Vous garantissez la conformité des installations et la satisfaction des clients.",
            'missions': [
                "Lire et interpréter les plans et schémas électriques",
                "Réaliser les installations neuves et les rénovations (courant fort et courant faible)",
                "Câbler et raccorder les tableaux électriques",
                "Effectuer les mesures, essais et mises en service",
                "Diagnostiquer et dépanner les installations existantes",
            ],
            'niveau': "BT / BTS électrotechnique, 2 ans d'expérience minimum",
        },
        'freelance': {
            'titre': "Freelance – Électricien(ne) bâtiment",
            'accroche': "Intervenez en renfort sur nos chantiers d'installation et de dépannage.",
            'description': "Nous recherchons des électriciens indépendants pour renforcer nos équipes lors des chantiers importants ou des interventions urgentes, à Lokossa et dans les communes environnantes.",
            'missions': [
                "Réaliser des installations ou rénovations sur un périmètre défini",
                "Intervenir en dépannage à la demande de KcoMat",
                "Effectuer les essais avant réception des travaux",
                "Transmettre photos et compte rendu de fin d'intervention",
            ],
            'niveau': "Expérience confirmée, outillage personnel",
        },
    },
    'electricite_industrielle': {
        'competences': [
            "Électrotechnique : moteurs, démarreurs, variateurs et protections",
            "Automatisme : programmation d'automates (Ladder, Grafcet), notions d'IHM",
            "Lecture de schémas : schémas de commande et de puissance",
            "Savoir-être : méthode, sens de l'analyse et respect strict de la sécurité",
        ],
        'profil': [
            "Attiré(e) par l'industrie et les machines",
            "Logique et méthodique dans le diagnostic",
            "Capable de travailler en environnement industriel",
        ],
        'stage': {
            'titre': "Stagiaire en électricité industrielle & automatisme",
            'accroche': "Découvrez les armoires électriques, les automates et la maintenance industrielle.",
            'description': "Vous accompagnez nos techniciens sur des projets d'automatisation et de maintenance pour des clients industriels et agricoles : armoires de commande, moteurs, variateurs et automates programmables.",
            'missions': [
                "Participer au câblage d'armoires électriques de commande et de puissance",
                "Découvrir la programmation d'automates (logique, temporisations, sécurités)",
                "Participer aux interventions de maintenance préventive et corrective",
                "Contrôler les moteurs, variateurs et capteurs industriels",
                "Mettre à jour les schémas et la documentation technique",
            ],
            'niveau': "BTS / DUT / Licence en électrotechnique, électromécanique ou automatisme",
        },
        'emploi': {
            'titre': "Technicien(ne) en automatisme industriel",
            'accroche': "Concevez et maintenez des systèmes automatisés pour l'industrie et l'agro-transformation.",
            'description': "Vous concevez, installez et maintenez des systèmes de commande automatisés : armoires électriques, automates, variateurs de vitesse et supervision. Vous intervenez chez des clients industriels, agricoles et agroalimentaires.",
            'missions': [
                "Étudier les besoins d'automatisation et rédiger l'analyse fonctionnelle",
                "Concevoir et câbler les armoires de commande et de puissance",
                "Programmer et mettre en service les automates et les IHM",
                "Assurer la maintenance et le diagnostic des pannes",
                "Former les opérateurs à l'utilisation des équipements",
            ],
            'niveau': "BTS / Licence en automatisme ou électrotechnique, 2 ans d'expérience",
        },
        'freelance': {
            'titre': "Freelance – Automaticien(ne)",
            'accroche': "Programmez et mettez en service des automates sur nos projets clients.",
            'description': "Pour certains projets, KcoMat collabore avec des automaticiens indépendants : programmation d'automates, mise en service d'armoires et modernisation d'installations existantes.",
            'missions': [
                "Programmer des automates selon l'analyse fonctionnelle fournie",
                "Participer aux essais et à la mise en service sur site",
                "Documenter les programmes et les modifications",
                "Assurer un support à distance après la mise en service",
            ],
            'niveau': "Expérience confirmée en programmation d'automates",
        },
    },
    'electronique': {
        'competences': [
            "Électronique : lecture et conception de schémas, composants, alimentations",
            "Programmation : C/C++ pour microcontrôleurs, notions de MicroPython",
            "Communication : UART, I2C, SPI, Wi-Fi, Bluetooth ou LoRa",
            "Savoir-être : curiosité, patience dans le débogage et goût du travail bien fait",
        ],
        'profil': [
            "Passionné(e) par l'électronique et la fabrication de prototypes",
            "Méthodique dans les tests et les mesures",
            "Capable de documenter clairement son travail",
        ],
        'stage': {
            'titre': "Stagiaire en électronique & systèmes embarqués",
            'accroche': "Concevez, programmez et testez des cartes électroniques avec ESP32, Arduino et capteurs.",
            'description': "Au sein de notre laboratoire, vous participez à la conception de prototypes électroniques : cartes à microcontrôleur, capteurs, modules de communication. Accompagné(e) par nos ingénieurs, vous passez de l'idée au prototype fonctionnel.",
            'missions': [
                "Concevoir et assembler des montages électroniques sur platine et circuit imprimé",
                "Programmer des microcontrôleurs (ESP32, Arduino, STM32) en C/C++ ou MicroPython",
                "Intégrer capteurs, actionneurs et modules de communication (Wi-Fi, Bluetooth, LoRa)",
                "Tester, mesurer et documenter les prototypes",
                "Participer à la préparation des kits de formation KcoMat",
            ],
            'niveau': "BTS / Licence en électronique, électrotechnique ou informatique industrielle",
        },
        'emploi': {
            'titre': "Ingénieur(e) / technicien(ne) en systèmes embarqués",
            'accroche': "Développez des produits électroniques connectés, du schéma au firmware.",
            'description': "Vous prenez en charge des projets de produits électroniques connectés pour nos clients et pour nos formations : conception des schémas, routage des cartes, développement du firmware et tests.",
            'missions': [
                "Concevoir les schémas électroniques et router les circuits imprimés",
                "Développer le firmware des microcontrôleurs (C/C++, MicroPython)",
                "Mettre en place la communication avec le cloud (MQTT, API)",
                "Réaliser les tests, la validation et la documentation",
                "Contribuer aux contenus pédagogiques de KcoMat",
            ],
            'niveau': "Licence / Master en électronique ou systèmes embarqués, 1 à 3 ans d'expérience",
        },
        'freelance': {
            'titre': "Freelance – Développeur(se) firmware",
            'accroche': "Développez des firmwares et des prototypes pour nos projets embarqués.",
            'description': "KcoMat confie à des indépendants la réalisation de prototypes ou de firmwares pour des projets clairement définis : capteurs connectés, cartes de commande, objets IoT.",
            'missions': [
                "Développer ou faire évoluer un firmware selon un cahier des charges",
                "Réaliser un prototype fonctionnel et ses tests",
                "Livrer le code source documenté",
                "Accompagner l'équipe lors de l'intégration",
            ],
            'niveau': "Expérience confirmée en développement embarqué",
        },
    },
    'web_mobile': {
        'competences': [
            "Web : HTML, CSS, JavaScript et un framework (Django, Laravel ou équivalent)",
            "Bases de données : SQL et conception de modèles de données",
            "Outils : Git, déploiement et bonnes pratiques de sécurité",
            "Savoir-être : autonomie, sens du détail et esprit d'équipe",
        ],
        'profil': [
            "Curieux(se) des nouvelles technologies",
            "Soucieux(se) de l'expérience utilisateur",
            "Organisé(e) et à l'écoute des besoins clients",
        ],
        'stage': {
            'titre': "Stagiaire développeur(se) web & mobile",
            'accroche': "Participez à la création de sites, d'applications et de tableaux de bord pour nos clients.",
            'description': "Au sein de notre pôle numérique, vous participez au développement de sites web, d'applications mobiles et d'interfaces de pilotage pour nos projets IoT. Vous travaillez sur des projets réels, avec revue de code et accompagnement.",
            'missions': [
                "Développer des pages et des fonctionnalités web (HTML, CSS, JavaScript, Python/Django)",
                "Participer à la création d'applications mobiles ou web progressives",
                "Intégrer des API et des données issues de nos objets connectés",
                "Tester les fonctionnalités et corriger les anomalies",
                "Rédiger la documentation technique",
            ],
            'niveau': "BTS / Licence en informatique, génie logiciel ou développement web",
        },
        'emploi': {
            'titre': "Développeur(se) web & mobile full-stack",
            'accroche': "Concevez les applications web et mobiles de KcoMat et de ses clients.",
            'description': "Vous concevez et développez des applications web et mobiles complètes : sites vitrines, plateformes de gestion, tableaux de bord IoT. Vous intervenez de la conception à la mise en production et à la maintenance.",
            'missions': [
                "Concevoir l'architecture des applications et des bases de données",
                "Développer le front-end et le back-end (Django, API REST, JavaScript)",
                "Intégrer les paiements Mobile Money et les services tiers",
                "Déployer, sécuriser et maintenir les applications en production",
                "Accompagner les stagiaires du pôle numérique",
            ],
            'niveau': "Licence / Master en informatique, 2 ans d'expérience en développement",
        },
        'freelance': {
            'titre': "Freelance – Développeur(se) web",
            'accroche': "Réalisez des sites et des applications pour nos clients, en mission.",
            'description': "KcoMat confie à des développeurs indépendants la réalisation de sites web et d'applications, sur la base d'un cahier des charges et de maquettes validées par le client.",
            'missions': [
                "Développer un site ou une application selon le cahier des charges",
                "Respecter les délais et les jalons de livraison",
                "Livrer un code propre, documenté et versionné (Git)",
                "Assurer la correction des anomalies après livraison",
            ],
            'niveau': "Portfolio de réalisations exigé",
        },
    },
    'ia': {
        'competences': [
            "Programmation : Python (pandas, NumPy, scikit-learn)",
            "IA : notions de deep learning (TensorFlow, PyTorch) et de vision par ordinateur",
            "Données : nettoyage, visualisation et statistiques de base",
            "Savoir-être : esprit d'analyse, rigueur et capacité à vulgariser",
        ],
        'profil': [
            "Passionné(e) par l'IA et ses applications concrètes",
            "À l'aise avec les chiffres et le raisonnement logique",
            "Capable d'expliquer simplement des résultats techniques",
        ],
        'stage': {
            'titre': "Stagiaire en intelligence artificielle & data",
            'accroche': "Entraînez des modèles d'IA et exploitez des données sur des cas concrets africains.",
            'description': "Vous participez à nos projets d'intelligence artificielle appliquée : vision par ordinateur, analyse de données de capteurs et IA embarquée (Edge AI). Vous travaillez sur des données réelles et des cas d'usage locaux.",
            'missions': [
                "Collecter, nettoyer et annoter des jeux de données",
                "Entraîner et évaluer des modèles de machine learning",
                "Participer à des projets de vision par ordinateur (détection, reconnaissance)",
                "Tester le déploiement de modèles légers sur cartes embarquées",
                "Présenter les résultats sous forme de tableaux de bord",
            ],
            'niveau': "Licence / Master en informatique, mathématiques appliquées ou data science",
        },
        'emploi': {
            'titre': "Ingénieur(e) IA & data",
            'accroche': "Concevez des solutions d'IA appliquée, du cloud jusqu'aux objets embarqués.",
            'description': "Vous concevez et déployez des solutions d'intelligence artificielle pour nos clients et nos formations : analyse de données, vision par ordinateur et modèles embarqués. Vous participez aussi à la conception de nos programmes de formation en IA.",
            'missions': [
                "Analyser les besoins et définir les cas d'usage de l'IA",
                "Concevoir, entraîner et optimiser les modèles",
                "Déployer les modèles (API, applications, cartes embarquées)",
                "Mettre en place le suivi de la qualité des données et des modèles",
                "Contribuer aux formations IA de KcoMat",
            ],
            'niveau': "Master en data science / IA ou équivalent, 1 à 3 ans d'expérience",
        },
        'freelance': {
            'titre': "Freelance – Data scientist",
            'accroche': "Prenez en charge des missions d'analyse de données et de modèles d'IA.",
            'description': "Pour des missions ponctuelles, KcoMat fait appel à des data scientists indépendants : études de données, prototypes de modèles, tableaux de bord d'aide à la décision.",
            'missions': [
                "Analyser un jeu de données et en extraire des indicateurs utiles",
                "Développer un prototype de modèle prédictif ou de vision",
                "Livrer le code, les résultats et une note de synthèse",
                "Présenter les conclusions à l'équipe et au client",
            ],
            'niveau': "Expérience confirmée, exemples de projets exigés",
        },
    },
    'drones': {
        'competences': [
            "Pilotage : maîtrise du vol manuel et des modes automatiques",
            "Réglementation : règles de vol et de sécurité applicables aux drones",
            "Technique : assemblage, réglages et maintenance de base",
            "Image : traitement photo/vidéo et logiciels de cartographie (appréciés)",
        ],
        'profil': [
            "Calme et concentré(e) en situation de vol",
            "Rigoureux(se) dans la préparation et les checklists",
            "Mobile et à l'aise sur le terrain",
        ],
        'stage': {
            'titre': "Stagiaire télépilote & technicien(ne) drone",
            'accroche': "Préparez, pilotez et entretenez des drones pour la cartographie, l'agriculture et l'image.",
            'description': "Au sein de notre pôle drones, vous participez aux missions de prise de vue aérienne, de cartographie et de surveillance agricole, ainsi qu'à l'entretien et à l'assemblage des appareils.",
            'missions': [
                "Préparer les missions de vol (météo, zone, plan de vol, checklists)",
                "Piloter en assistance du télépilote référent",
                "Assembler, régler et entretenir les drones",
                "Traiter les images et les données collectées (photos, cartes, orthophotos)",
                "Participer à l'animation des formations au pilotage",
            ],
            'niveau': "Bac à Licence, intérêt marqué pour l'aéronautique ou l'électronique",
        },
        'emploi': {
            'titre': "Télépilote de drone & technicien(ne) de maintenance",
            'accroche': "Réalisez des missions aériennes professionnelles et assurez la maintenance de notre flotte.",
            'description': "Vous réalisez des missions professionnelles par drone (cartographie, inspection, image, agriculture de précision) et assurez la maintenance de la flotte KcoMat. Vous intervenez également comme formateur.",
            'missions': [
                "Planifier et réaliser les missions de vol en toute sécurité",
                "Traiter les données aériennes et produire les livrables clients",
                "Assurer la maintenance préventive et les réparations des drones",
                "Animer des sessions de formation au pilotage",
                "Veiller au respect de la réglementation en vigueur",
            ],
            'niveau': "Expérience de pilotage professionnel, connaissance de la réglementation",
        },
        'freelance': {
            'titre': "Freelance – Télépilote de drone",
            'accroche': "Réalisez des prises de vue et des relevés aériens pour nos clients.",
            'description': "KcoMat collabore avec des télépilotes indépendants pour des missions ponctuelles : prises de vue d'événements, inspections, cartographie de parcelles.",
            'missions': [
                "Réaliser la mission de vol selon le brief du client",
                "Livrer les images et les données dans les délais",
                "Respecter les règles de sécurité et la réglementation",
                "Fournir un compte rendu de mission",
            ],
            'niveau': "Expérience de pilotage confirmée, matériel personnel apprécié",
        },
    },
    'solaire': {
        'competences': [
            "Électricité : courant continu et alternatif, protections et câblage",
            "Solaire : panneaux, régulateurs, onduleurs et batteries",
            "Dimensionnement : calcul des besoins et de l'autonomie",
            "Savoir-être : sécurité en hauteur, rigueur et sens du service",
        ],
        'profil': [
            "Sensible aux énergies renouvelables",
            "À l'aise pour travailler en hauteur et en extérieur",
            "Pédagogue avec les clients",
        ],
        'stage': {
            'titre': "Stagiaire technicien(ne) solaire photovoltaïque",
            'accroche': "Participez au dimensionnement et à l'installation de systèmes solaires autonomes et raccordés.",
            'description': "Vous accompagnez nos techniciens sur des projets d'installation photovoltaïque : kits solaires domestiques, systèmes autonomes avec batteries et installations pour les entreprises et les exploitations agricoles.",
            'missions': [
                "Participer au dimensionnement des installations (besoins, panneaux, batteries, onduleurs)",
                "Poser et raccorder les panneaux, régulateurs, batteries et onduleurs",
                "Réaliser les mesures et la mise en service",
                "Participer à la maintenance des installations existantes",
                "Sensibiliser les clients à la bonne utilisation de leur système",
            ],
            'niveau': "BT / BTS / Licence en électrotechnique ou énergies renouvelables",
        },
        'emploi': {
            'titre': "Technicien(ne) installateur solaire photovoltaïque",
            'accroche': "Concevez et installez des solutions solaires fiables pour les foyers et les entreprises.",
            'description': "Vous prenez en charge les projets solaires de A à Z : visite technique, dimensionnement, devis, installation, mise en service et suivi. Vous contribuez à l'accès à une énergie fiable et durable au Bénin.",
            'missions': [
                "Réaliser les visites techniques et les études de dimensionnement",
                "Établir les listes de matériel et participer aux devis",
                "Installer et mettre en service les systèmes photovoltaïques",
                "Assurer la maintenance et le dépannage",
                "Former les clients à l'entretien de leur installation",
            ],
            'niveau': "BTS / Licence en électrotechnique ou énergies renouvelables, 2 ans d'expérience",
        },
        'freelance': {
            'titre': "Freelance – Installateur(trice) solaire",
            'accroche': "Installez des systèmes solaires pour nos clients, en renfort de nos équipes.",
            'description': "Nous faisons appel à des installateurs indépendants pour réaliser des installations photovoltaïques sur la base d'un dimensionnement validé par KcoMat.",
            'missions': [
                "Installer le système selon le dimensionnement fourni",
                "Réaliser les essais et la mise en service",
                "Expliquer le fonctionnement au client",
                "Remettre un rapport d'installation avec photos",
            ],
            'niveau': "Expérience confirmée en installation photovoltaïque",
        },
    },
    'securite': {
        'competences': [
            "Réseaux : TCP/IP, VLAN, routage, Wi-Fi et VPN",
            "Sécurité : pare-feu, gestion des accès, sauvegardes et chiffrement",
            "Systèmes : administration Windows et Linux",
            "Savoir-être : discrétion, éthique professionnelle et rigueur",
        ],
        'profil': [
            "Curieux(se) et en veille permanente",
            "Discret(ète) et digne de confiance",
            "Pédagogue pour sensibiliser les utilisateurs",
        ],
        'stage': {
            'titre': "Stagiaire en sécurité informatique & réseaux",
            'accroche': "Sécurisez des réseaux, testez des systèmes et sensibilisez les utilisateurs.",
            'description': "Vous participez à nos missions d'installation et de sécurisation de réseaux informatiques pour des entreprises, des écoles et des administrations, ainsi qu'à nos actions de sensibilisation à la cybersécurité.",
            'missions': [
                "Participer à l'installation et à la configuration de réseaux (routeurs, switchs, Wi-Fi)",
                "Mettre en place des mesures de sécurité de base (pare-feu, mots de passe, sauvegardes)",
                "Réaliser des audits simples et des tests de vulnérabilité encadrés",
                "Rédiger des fiches de bonnes pratiques pour les utilisateurs",
                "Participer au support informatique des clients",
            ],
            'niveau': "BTS / Licence en réseaux, télécommunications ou sécurité informatique",
        },
        'emploi': {
            'titre': "Administrateur(trice) réseaux & cybersécurité",
            'accroche': "Protégez les systèmes de nos clients et pilotez leurs infrastructures réseau.",
            'description': "Vous concevez, déployez et sécurisez les infrastructures réseau de nos clients. Vous menez des audits, mettez en place les protections nécessaires et accompagnez les équipes dans l'adoption de bonnes pratiques.",
            'missions': [
                "Concevoir et déployer des architectures réseau sécurisées",
                "Administrer pare-feu, VPN, Wi-Fi et sauvegardes",
                "Réaliser des audits de sécurité et proposer des plans d'action",
                "Gérer les incidents et assurer la veille sécurité",
                "Animer des formations de sensibilisation",
            ],
            'niveau': "Licence / Master en réseaux ou cybersécurité, 2 ans d'expérience",
        },
        'freelance': {
            'titre': "Freelance – Consultant(e) cybersécurité",
            'accroche': "Menez des audits et des actions de sécurisation pour nos clients.",
            'description': "KcoMat fait appel à des consultants indépendants pour des missions d'audit, de durcissement des systèmes et de sensibilisation, auprès d'entreprises et d'institutions.",
            'missions': [
                "Réaliser un audit de sécurité selon le périmètre défini",
                "Rédiger un rapport de vulnérabilités et de recommandations",
                "Accompagner la mise en œuvre des correctifs",
                "Animer une session de sensibilisation",
            ],
            'niveau': "Expérience confirmée, certifications appréciées",
        },
    },
    'videosurveillance': {
        'competences': [
            "Électronique : câblage courant faible, alimentations et protections",
            "Réseaux : adressage IP, configuration de routeurs et accès à distance",
            "Équipements : caméras IP, enregistreurs NVR/DVR, alarmes et contrôle d'accès",
            "Savoir-être : discrétion, rigueur et sens du service",
        ],
        'profil': [
            "Soigneux(se) dans la pose et les finitions",
            "Discret(ète) et respectueux(se) de la confidentialité",
            "À l'aise pour expliquer l'utilisation aux clients",
        ],
        'stage': {
            'titre': "Stagiaire installateur(trice) vidéosurveillance",
            'accroche': "Installez caméras, alarmes et contrôles d'accès pour sécuriser bâtiments et commerces.",
            'description': "Vous accompagnez nos techniciens lors de l'installation de systèmes de sécurité électronique : caméras IP, enregistreurs, alarmes anti-intrusion et contrôle d'accès, pour des particuliers et des entreprises.",
            'missions': [
                "Participer au repérage et au positionnement des caméras",
                "Poser, câbler et raccorder caméras, enregistreurs et alarmes",
                "Configurer l'accès à distance sur smartphone",
                "Tester les installations et former les utilisateurs",
                "Participer à la maintenance des systèmes installés",
            ],
            'niveau': "BT / BTS en électronique, électrotechnique ou réseaux",
        },
        'emploi': {
            'titre': "Technicien(ne) en sécurité électronique",
            'accroche': "Concevez et installez des systèmes de vidéosurveillance et d'alarme fiables.",
            'description': "Vous concevez et installez des systèmes de sécurité électronique complets, adaptés à chaque site : vidéosurveillance, détection d'intrusion, contrôle d'accès et supervision à distance.",
            'missions': [
                "Réaliser les études de site et proposer les solutions adaptées",
                "Installer et paramétrer caméras IP, enregistreurs et alarmes",
                "Configurer les réseaux et l'accès à distance sécurisé",
                "Assurer la maintenance et le dépannage",
                "Conseiller les clients sur l'évolution de leur installation",
            ],
            'niveau': "BTS / Licence en électronique ou réseaux, 2 ans d'expérience",
        },
        'freelance': {
            'titre': "Freelance – Installateur(trice) vidéosurveillance",
            'accroche': "Réalisez des installations de caméras et d'alarmes en renfort de nos équipes.",
            'description': "Nous collaborons avec des installateurs indépendants pour des chantiers de vidéosurveillance et d'alarme, sur la base d'une étude réalisée par KcoMat.",
            'missions': [
                "Installer le matériel selon le plan d'implantation",
                "Paramétrer l'enregistrement et l'accès à distance",
                "Tester l'installation et la faire valider par le client",
                "Remettre un rapport d'intervention",
            ],
            'niveau': "Expérience confirmée en sécurité électronique",
        },
    },
    'commercial': {
        'competences': [
            "Communication : aisance à l'oral et à l'écrit, sens de l'écoute",
            "Commerce : techniques de vente, négociation et suivi client",
            "Numérique : réseaux sociaux, WhatsApp Business et outils bureautiques",
            "Savoir-être : dynamisme, persévérance et intérêt pour la technologie",
        ],
        'profil': [
            "Souriant(e) et à l'aise avec le public",
            "Persévérant(e) et orienté(e) résultats",
            "Intéressé(e) par la technologie",
        ],
        'stage': {
            'titre': "Stagiaire commercial(e) & relation client",
            'accroche': "Conseillez nos clients sur nos formations, nos composants et nos services technologiques.",
            'description': "Vous rejoignez l'équipe commerciale de KcoMat pour faire connaître nos formations, notre boutique de composants et nos services. Vous êtes au contact des clients : en boutique, au téléphone et sur les réseaux sociaux.",
            'missions': [
                "Accueillir, conseiller et orienter les clients (boutique, téléphone, WhatsApp)",
                "Présenter nos formations et nos services aux particuliers et aux entreprises",
                "Participer à la prospection et aux actions de communication",
                "Suivre les demandes de devis et les relances",
                "Animer nos pages sur les réseaux sociaux",
            ],
            'niveau': "BTS / Licence en commerce, marketing ou communication",
        },
        'emploi': {
            'titre': "Chargé(e) commercial(e) solutions technologiques",
            'accroche': "Développez le portefeuille clients de KcoMat auprès des entreprises et des institutions.",
            'description': "Vous développez les ventes de formations, de composants et de solutions technologiques auprès des particuliers, des entreprises, des écoles et des institutions. Vous construisez des relations durables avec nos clients.",
            'missions': [
                "Prospecter et développer un portefeuille de clients",
                "Comprendre les besoins et proposer des offres adaptées",
                "Établir les devis et suivre les négociations",
                "Fidéliser les clients et suivre leur satisfaction",
                "Faire remonter les besoins du terrain à l'équipe technique",
            ],
            'niveau': "Licence en commerce ou équivalent, 2 ans d'expérience commerciale",
        },
        'freelance': {
            'titre': "Freelance – Apporteur(se) d'affaires",
            'accroche': "Recommandez nos formations et nos services, et percevez une commission.",
            'description': "Vous disposez d'un réseau auprès d'écoles, d'entreprises ou d'institutions ? Devenez apporteur d'affaires pour KcoMat et percevez une commission sur chaque client signé.",
            'missions': [
                "Identifier des prospects intéressés par nos formations ou nos services",
                "Organiser une première prise de contact avec l'équipe KcoMat",
                "Suivre l'avancement des opportunités transmises",
                "Représenter l'image de KcoMat avec professionnalisme",
            ],
            'niveau': "Bon réseau professionnel, aucun diplôme exigé",
            'remuneration': "Commission sur chaque client signé",
        },
    },
}


def slug_catalogue(type_offre, domaine):
    return f"{type_offre}-{domaine}".replace('_', '-')


@transaction.atomic
def charger_catalogue(force=False):
    """
    Crée les offres du catalogue absentes (masquées, sans image).
    force=True réécrit aussi les textes des offres du catalogue déjà présentes
    (sans toucher à l'image, à la publication ni à la date limite).
    Retourne (créées, mises à jour, inchangées).
    """
    from .models import FormuleOffre, Offre

    crees, maj, inchangees = 0, 0, 0
    for domaine, contenu in DOMAINES.items():
        for type_offre in ('stage', 'emploi', 'freelance'):
            fiche = contenu[type_offre]
            reglages = REGLAGES_TYPE[type_offre]
            champs = {
                'titre': fiche['titre'],
                'type_offre': type_offre,
                'domaine': domaine,
                'accroche': fiche['accroche'],
                'description': fiche['description'],
                'missions': '\n'.join(fiche['missions']),
                'competences_requises': '\n'.join(contenu['competences']),
                'profil': '\n'.join([PROFIL_TYPE[type_offre], *contenu['profil']]),
                'avantages': '\n'.join(AVANTAGES[type_offre]),
                'niveau_requis': fiche['niveau'],
                'nature_montant': reglages['nature_montant'],
                'remuneration': fiche.get('remuneration', reglages['remuneration']),
                'places': reglages['places'],
            }
            offre = Offre.objects.filter(slug=slug_catalogue(type_offre, domaine)).first()
            if offre is None:
                offre = Offre.objects.create(slug=slug_catalogue(type_offre, domaine), actif=False, **champs)
                crees += 1
            elif force:
                for nom, valeur in champs.items():
                    setattr(offre, nom, valeur)
                offre.save()
                offre.formules.all().delete()
                maj += 1
            else:
                inchangees += 1
                continue
            if type_offre == 'stage':
                FormuleOffre.objects.bulk_create(FormuleOffre(offre=offre, **f) for f in FORMULES_STAGE)
    return crees, maj, inchangees
