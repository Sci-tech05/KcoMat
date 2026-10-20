"""
Libellés français des champs de modèles (admin, formulaires, exports).

Appliqués au démarrage (CoreConfig.ready) aux seuls champs dont le libellé est
celui généré automatiquement par Django à partir du nom (ex. « created at »).
Un verbose_name défini explicitement dans un modèle reste toujours prioritaire.
"""
from django.apps import apps

APPS_KCOMAT = ('accounts', 'boutique', 'carrieres', 'core', 'formations', 'partenariats', 'projets', 'services')

LIBELLES = {
    'accroche': 'Accroche', 'actif': 'Actif', 'adresse': 'Adresse', 'adresse_livraison': 'Adresse de livraison',
    'alt': 'Texte alternatif', 'bio': 'Biographie', 'budget_estime': 'Budget estimé', 'categorie': 'Catégorie',
    'client': 'Client', 'commande': 'Commande', 'couleur': 'Couleur', 'created_at': 'Créé le', 'cv': 'CV',
    'date_debut': 'Date de début', 'date_fin': 'Date de fin', 'date_limite': 'Date limite',
    'date_realisation': 'Date de réalisation', 'description': 'Description', 'description_besoin': 'Description du besoin',
    'description_courte': 'Description courte', 'description_projet': 'Description du projet', 'domaine': 'Domaine',
    'duree': 'Durée', 'email': 'E-mail', 'en_vedette': 'En vedette', 'fedapay_formation_id': 'Transaction Fedapay (formation)',
    'fedapay_frais_id': 'Transaction Fedapay (frais)', 'fedapay_transaction_id': 'Transaction Fedapay', 'fichier': 'Fichier',
    'formation': 'Formation', 'formation_payee_le': 'Formation payée le', 'frais_payes_le': 'Frais payés le', 'icone': 'Icône',
    'image': 'Image', 'image_couverture': 'Image de couverture', 'image_principale': 'Image principale',
    'jitsi_room_created_at': 'Salle créée le', 'jitsi_room_name': 'Salle Jitsi', 'legende': 'Légende',
    'lettre_motivation': 'Lettre de motivation', 'libelle': 'Libellé', 'linkedin': 'LinkedIn', 'localite': 'Localité',
    'logo': 'Logo', 'lu': 'Lu', 'message': 'Message', 'mode_preference': 'Mode', 'montant_total': 'Montant total',
    'niveau': 'Niveau', 'niveau_actuel': 'Niveau actuel', 'niveau_requis': 'Niveau requis', 'nom': 'Nom',
    'nom_contact': 'Nom du contact', 'nom_organisation': "Nom de l'organisation", 'nom_produit': 'Produit', 'note': 'Note',
    'notes': 'Notes', 'nouveau': 'Nouveau', 'objectifs': 'Objectifs', 'offre': 'Offre', 'ordre': 'Ordre', 'panier': 'Panier',
    'payee_le': 'Payée le', 'periode': 'Période', 'photo': 'Photo', 'places_disponibles': 'Places disponibles',
    'poste': 'Poste', 'prenom': 'Prénom', 'prerequis': 'Prérequis', 'prix': 'Prix', 'prix_avec_base': 'Prix avec base',
    'prix_unitaire': 'Prix unitaire', 'produit': 'Produit', 'projet': 'Projet', 'publiee': 'Publiée', 'quantite': 'Quantité',
    'reference': 'Référence', 'resume': 'Résumé', 'service': 'Service', 'session': 'Session', 'session_key': 'Clé de session',
    'site_web': 'Site web', 'slug': 'Adresse (slug)', 'statut': 'Statut', 'statut_modifie_le': 'Statut modifié le',
    'stock': 'Stock', 'sujet': 'Sujet', 'technologies': 'Technologies', 'telephone': 'Téléphone', 'texte': 'Texte',
    'titre': 'Titre', 'traite': 'Traité', 'type_media': 'Type de média', 'type_organisation': "Type d'organisation",
    'type_partenaire': 'Type de partenaire', 'type_partenariat_souhaite': 'Type de partenariat souhaité',
    'updated_at': 'Mis à jour le', 'url': 'Lien', 'utilisateur': 'Utilisateur', 'valeur': 'Valeur',
    'video_apercu_file': "Vidéo d'aperçu (fichier)", 'video_apercu_url': "Vidéo d'aperçu (lien)", 'video_file': 'Fichier vidéo',
    'video_principale': 'Vidéo principale', 'video_url': 'Lien vidéo', 'ville': 'Ville',
}


def appliquer_libelles():
    for app_label in APPS_KCOMAT:
        for model in apps.get_app_config(app_label).get_models():
            for field in model._meta.get_fields():
                if not getattr(field, 'concrete', False) or field.auto_created:
                    continue
                if str(field.verbose_name) == field.name.replace('_', ' ') and field.name in LIBELLES:
                    field.verbose_name = LIBELLES[field.name]
