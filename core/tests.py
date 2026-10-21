from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from boutique.models import Commande, CommandeItem, Produit
from formations.models import Formation, Inscription
from .models import Avis


class AvisTests(TestCase):
    def setUp(self):
        self.produit = Produit.objects.create(nom='ESP32', slug='esp32-avis', description_courte='x', description='x', prix=10000, stock=5)
        self.client_kc = User.objects.create_user('ama', 'ama@example.com', 'pw-ama-12345', first_name='Ama', last_name='Kossi')
        self.url = reverse('core:donner_avis', args=['produit', self.produit.pk])

    def test_connexion_obligatoire(self):
        reponse = self.client.post(self.url, {'note': 5})
        self.assertEqual(reponse.status_code, 302)
        self.assertIn(reverse('accounts:connexion'), reponse.url)
        self.assertFalse(Avis.objects.exists())

    def test_un_seul_avis_par_client_mis_a_jour(self):
        self.client.force_login(self.client_kc)
        self.client.post(self.url, {'note': 2, 'commentaire': 'Bof'})
        reponse = self.client.post(self.url, {'note': 5, 'commentaire': 'Finalement top'})
        self.assertRedirects(reponse, reverse('boutique:detail', args=[self.produit.slug]) + '#avis', fetch_redirect_response=False)
        self.assertEqual(Avis.objects.count(), 1)
        self.assertEqual(Avis.objects.get().note, 5)

    def test_note_invalide_refusee(self):
        self.client.force_login(self.client_kc)
        self.client.post(self.url, {'note': 9})
        self.assertFalse(Avis.objects.exists())

    def test_achat_verifie_seulement_si_commande_payee(self):
        commande = Commande.objects.create(utilisateur=self.client_kc, nom='K', prenom='A', email='a@x.com', telephone='1',
                                           adresse_livraison='r', ville='Lokossa', montant_total=10000)
        CommandeItem.objects.create(commande=commande, produit=self.produit, nom_produit='ESP32', prix_unitaire=10000, quantite=1)
        self.client.force_login(self.client_kc)
        self.client.post(self.url, {'note': 4})
        self.assertFalse(Avis.objects.get().achat_verifie)      # commande pas encore payée
        commande.statut = 'livree'
        commande.save()
        self.client.post(self.url, {'note': 4})
        self.assertTrue(Avis.objects.get().achat_verifie)

    def test_page_affiche_moyenne_et_donnees_google(self):
        autre = User.objects.create_user('kofi', 'k@example.com', 'pw')
        for u, note in ((self.client_kc, 5), (autre, 4)):
            Avis.objects.create(objet=self.produit, utilisateur=u, note=note, commentaire='Très bon module')
        Avis.objects.create(objet=self.produit, utilisateur=User.objects.create_user('spam'), note=1, publie=False)
        reponse = self.client.get(reverse('boutique:detail', args=[self.produit.slug]))
        self.assertContains(reponse, '4,5')                       # moyenne des avis publiés uniquement
        self.assertContains(reponse, '"reviewCount": "2"')
        self.assertContains(reponse, 'Ama K.')                    # jamais le nom complet
        self.assertNotContains(reponse, 'Kossi')

    def test_avis_formation_participant_verifie(self):
        formation = Formation.objects.create(titre='Domotique', description_courte='IoT', description='IoT', prix=20000)
        Inscription.objects.create(formation=formation, utilisateur=self.client_kc, nom='K', prenom='A', email='a@x.com',
                                   telephone='1', statut='complet')
        self.client.force_login(self.client_kc)
        self.client.post(reverse('core:donner_avis', args=['formation', formation.pk]), {'note': 5})
        self.assertTrue(Avis.objects.get().achat_verifie)
        self.assertContains(self.client.get(reverse('formations:detail', args=[formation.slug])), 'Participant vérifié')

    def test_type_inconnu(self):
        self.client.force_login(self.client_kc)
        self.assertEqual(self.client.post(reverse('core:donner_avis', args=['projet', 1]), {'note': 5}).status_code, 404)
