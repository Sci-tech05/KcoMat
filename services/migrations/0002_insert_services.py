from django.db import migrations


SERVICES = [
    {
        'titre': 'Développement Web & Mobile',
        'slug': 'developpement-web-mobile',
        'icone': '🌐',
        'couleur': '#2563eb',
        'description_courte': 'Création de sites web et applications mobiles sur mesure pour votre activité.',
        'description': (
            'Nous concevons et développons des sites web et applications mobiles sur mesure, '
            'adaptés à vos besoins spécifiques.\n\n'
            'Nos prestations incluent :\n'
            '- Sites vitrine et portfolios professionnels\n'
            '- Applications web (Django, React, Vue.js)\n'
            '- Applications mobiles Android/iOS\n'
            '- E-commerce et boutiques en ligne\n'
            '- Maintenance et hébergement\n\n'
            'Chaque projet est développé avec les meilleures pratiques du secteur : '
            'responsive design, performance optimisée et sécurité garantie.'
        ),
        'ordre': 1,
    },
    {
        'titre': 'Domotique & IoT',
        'slug': 'domotique-iot',
        'icone': '🏠',
        'couleur': '#16a34a',
        'description_courte': 'Installation de maisons intelligentes avec capteurs et automatisation complète.',
        'description': (
            'Transformez votre maison ou votre entreprise en un espace intelligent et connecté.\n\n'
            'Nos prestations incluent :\n'
            '- Installation de systèmes domotiques (éclairage, climatisation, sécurité)\n'
            '- Conception de réseaux de capteurs IoT\n'
            '- Automatisation industrielle et domestique\n'
            '- Tableaux de bord de supervision\n'
            '- Contrôle à distance via smartphone\n\n'
            'Nos solutions utilisent des technologies fiables comme Arduino, ESP32, Raspberry Pi '
            'et les protocoles MQTT, Zigbee, Z-Wave.'
        ),
        'ordre': 2,
    },
    {
        'titre': 'Formation sur site',
        'slug': 'formation-sur-site',
        'icone': '🎓',
        'couleur': '#7c3aed',
        'description_courte': 'Formations techniques personnalisées dispensées dans vos locaux ou les nôtres.',
        'description': (
            'Nous proposons des formations techniques sur mesure, adaptées au niveau et aux objectifs '
            'de vos équipes.\n\n'
            'Domaines couverts :\n'
            '- Électronique et microcontrôleurs\n'
            '- Domotique et IoT\n'
            '- Programmation Python et développement web\n'
            '- Intelligence artificielle appliquée\n'
            '- Pilotage de drones\n\n'
            'Les formations peuvent être dispensées dans vos locaux ou dans nos ateliers à Lokossa. '
            'Chaque participant reçoit une attestation officielle KcoMat.'
        ),
        'ordre': 3,
    },
    {
        'titre': 'Électronique embarquée',
        'slug': 'electronique-embarquee',
        'icone': '🔌',
        'couleur': '#ea580c',
        'description_courte': 'Conception et développement de cartes électroniques et systèmes embarqués.',
        'description': (
            'Notre équipe de techniciens spécialisés conçoit des solutions électroniques embarquées '
            'adaptées à vos projets industriels ou personnels.\n\n'
            'Nos prestations incluent :\n'
            '- Conception de PCB (circuits imprimés)\n'
            '- Développement firmware (C, C++, MicroPython)\n'
            '- Prototypage rapide\n'
            '- Systèmes de contrôle industriel\n'
            '- Intégration de modules (GPS, GSM, Wi-Fi, Bluetooth)\n\n'
            'De la conception au prototype fonctionnel, nous accompagnons vos projets de bout en bout.'
        ),
        'ordre': 4,
    },
    {
        'titre': 'Sécurité informatique',
        'slug': 'securite-informatique',
        'icone': '🔒',
        'couleur': '#dc2626',
        'description_courte': 'Audit de sécurité et mise en place de caméras pour protéger vos systèmes.',
        'description': (
            'Protégez vos infrastructures numériques et physiques grâce à nos solutions de sécurité.\n\n'
            'Nos prestations incluent :\n'
            '- Audit de sécurité informatique\n'
            '- Installation de systèmes de vidéosurveillance (IP, CCTV)\n'
            '- Mise en place de pare-feu et VPN\n'
            '- Sécurisation de réseaux Wi-Fi\n'
            '- Formation sensibilisation à la cybersécurité\n\n'
            'Nous travaillons avec des équipements certifiés et éprouvés pour garantir '
            'la protection optimale de vos données et locaux.'
        ),
        'ordre': 5,
    },
    {
        'titre': 'Pilotage de drone',
        'slug': 'pilotage-de-drone',
        'icone': '🚁',
        'couleur': '#0284c7',
        'description_courte': 'Formation au pilotage et utilisation professionnelle de drones pour vos projets.',
        'description': (
            'Maîtrisez les drones pour des applications professionnelles variées.\n\n'
            'Nos prestations incluent :\n'
            '- Formation au pilotage de drones (débutant à avancé)\n'
            '- Prises de vue aériennes et cartographie\n'
            '- Inspection d\'infrastructures par drone\n'
            '- Agriculture de précision\n'
            '- Développement de systèmes autonomes\n\n'
            'Formations pratiques sur le terrain avec différents types de drones. '
            'Attestation de formation délivrée à la fin du parcours.'
        ),
        'ordre': 6,
    },
]


def insert_services(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    for data in SERVICES:
        Service.objects.get_or_create(
            slug=data['slug'],
            defaults={
                'titre': data['titre'],
                'icone': data['icone'],
                'couleur': data['couleur'],
                'description_courte': data['description_courte'],
                'description': data['description'],
                'ordre': data['ordre'],
                'actif': True,
            }
        )


def remove_services(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    slugs = [s['slug'] for s in SERVICES]
    Service.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(insert_services, remove_services),
    ]
