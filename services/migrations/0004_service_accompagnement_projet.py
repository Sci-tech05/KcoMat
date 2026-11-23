from django.db import migrations

SLUG = 'accompagnement-de-projet'

SERVICE = {
    'titre': 'Accompagnement de projet',
    'icone': '🧭',
    'couleur': '#7c3aed',
    'description_courte': "Du thème à la réalisation : consultation, liste des matériels et réalisation de votre "
                          "projet technique par KcoMat.",
    'description': (
        "Vous avez un projet technique (projet de fin d'études, prototype, système embarqué, objet connecté) ? "
        "KcoMat vous accompagne en trois étapes, de la structuration de l'idée jusqu'au prototype qui fonctionne.\n\n"
        "Une session de consultation transforme d'abord votre idée en un thème clair, avec ses fonctionnalités, "
        "ses contraintes techniques et la liste complète des matériels. Vous vous procurez ensuite ces matériels, "
        "chez nous ou ailleurs, puis notre équipe réalise le système : montage, programmation, tests, "
        "documentation et explication du fonctionnement.\n\n"
        "Vous gardez la main à chaque étape : la réalisation ne commence qu'après validation d'un devis par "
        "les deux parties."
    ),
    'ordre': 0,
}


def ajouter(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    Service.objects.get_or_create(slug=SLUG, defaults={**SERVICE, 'actif': True})


def retirer(apps, schema_editor):
    apps.get_model('services', 'Service').objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0003_demande_accompagnement'),
    ]

    operations = [
        migrations.RunPython(ajouter, retirer),
    ]
