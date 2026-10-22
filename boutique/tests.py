from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from boutique.models import Commande, Produit

FETCH = 'api.fedapay_service.fetch_fedapay_transaction'


def fake_transactions(transactions):
    return lambda transaction_id: transactions.get(str(transaction_id), {})


def tx(tx_id, amount, status='approved', metadata=None):
    data = {'id': tx_id, 'status': status, 'amount': amount, 'currency': {'iso': 'XOF'}}
    if metadata is not None:
        data['custom_metadata'] = metadata
    return data


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CommandeSecurityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw-owner-123')
        self.other = User.objects.create_user('other', password='pw-other-123')
        self.commande = Commande.objects.create(
            utilisateur=self.owner, nom='Doe', prenom='Jane', email='jane@example.com',
            telephone='0100000000', adresse_livraison='Rue 1', ville='Lokossa',
            montant_total=150000, fedapay_transaction_id='30',
        )

    def test_unrelated_approved_transaction_cannot_pay_the_order(self):
        """Une transaction approuvée de 2 000 FCFA passée en ?id= ne paie pas une commande de 150 000."""
        txs = {
            '30': tx(30, 150000, status='pending'),
            '10': tx(10, 2000, metadata={'type': 'inscription_frais', 'inscription_id': '1'}),
        }
        self.client.force_login(self.owner)
        with patch(FETCH, side_effect=fake_transactions(txs)):
            self.client.get(reverse('boutique:succes_commande', args=[self.commande.pk]), {'id': '10'})
            self.client.get(reverse('boutique:callback', args=[self.commande.pk]), {'id': '10', 'status': 'approved'})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'en_attente')

    def test_underpaid_stored_transaction_is_rejected(self):
        with patch(FETCH, side_effect=fake_transactions({'30': tx(30, 1000)})):
            self.client.get(reverse('boutique:callback', args=[self.commande.pk]), {'status': 'approved'})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'en_attente')

    def test_real_payment_is_accepted(self):
        txs = {'30': tx(30, 150000, metadata={'type': 'commande', 'commande_id': str(self.commande.pk)})}
        with patch(FETCH, side_effect=fake_transactions(txs)):
            self.client.get(reverse('boutique:callback', args=[self.commande.pk]), {'id': '30', 'status': 'approved'})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'payee')

    def test_other_user_cannot_access_order(self):
        self.client.force_login(self.other)
        for name in ('boutique:facture_commande', 'boutique:succes_commande', 'boutique:paiement'):
            response = self.client.get(reverse(name, args=[self.commande.pk]))
            self.assertEqual(response.status_code, 403, name)

    def test_anonymous_order_not_readable_by_strangers(self):
        anonymous = Commande.objects.create(
            nom='Anon', prenom='A', email='a@example.com', telephone='0100000001',
            adresse_livraison='Rue 2', ville='Cotonou', montant_total=5000,
        )
        self.assertEqual(
            self.client.get(reverse('boutique:facture_commande', args=[anonymous.pk])).status_code, 403,
        )


class PanierSansRechargementTests(TestCase):
    """Retrait / quantité en JSON (static/js/panier.js) et repli classique sans JavaScript."""

    def setUp(self):
        from boutique.models import Panier, PanierItem, Produit
        self.user = User.objects.create_user('client-panier', password='x')
        self.client.force_login(self.user)
        p1 = Produit.objects.create(nom='ESP32', slug='esp32-t', description_courte='x', description='x', prix=10000, stock=5)
        p2 = Produit.objects.create(nom='Relais', slug='relais-t', description_courte='x', description='x', prix=2500, stock=5)
        self.panier = Panier.objects.create(utilisateur=self.user)
        self.i1 = PanierItem.objects.create(panier=self.panier, produit=p1, quantite=2)
        self.i2 = PanierItem.objects.create(panier=self.panier, produit=p2, quantite=1)
        self.json = {'HTTP_X_REQUESTED_WITH': 'fetch', 'HTTP_ACCEPT': 'application/json'}

    def test_retrait_json(self):
        r = self.client.post(reverse('boutique:supprimer_item', args=[self.i1.pk]), **self.json)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'ok': True, 'nombre_articles': 1, 'total': 2500, 'vide': False, 'supprime': True})
        r = self.client.post(reverse('boutique:supprimer_item', args=[self.i2.pk]), **self.json)
        self.assertTrue(r.json()['vide'])

    def test_quantite_json_plafonnee_au_stock(self):
        r = self.client.post(reverse('boutique:modifier_item', args=[self.i1.pk]), {'quantite': 99}, **self.json)
        self.assertEqual(r.json()['item'], {'quantite': 5, 'sous_total': 50000})
        self.assertEqual(r.json()['total'], 52500)
        r = self.client.post(reverse('boutique:modifier_item', args=[self.i1.pk]), {'quantite': 'abc'}, **self.json)
        self.assertEqual(r.json()['item']['quantite'], 1)

    def test_article_d_un_autre_panier_intouchable(self):
        from boutique.models import PanierItem
        autre = User.objects.create_user('autre', password='x')
        self.client.force_login(autre)
        self.client.post(reverse('boutique:supprimer_item', args=[self.i1.pk]), **self.json)
        self.assertTrue(PanierItem.objects.filter(pk=self.i1.pk).exists())

    def test_repli_sans_javascript(self):
        r = self.client.post(reverse('boutique:supprimer_item', args=[self.i1.pk]))
        self.assertRedirects(r, reverse('boutique:panier'))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SuiviCommandeTests(TestCase):
    def setUp(self):
        self.client_kc = User.objects.create_user('ama', 'ama@example.com', 'pw-ama-12345')
        self.commande = Commande.objects.create(
            utilisateur=self.client_kc, nom='Kossi', prenom='Ama', email='ama@example.com', telephone='1',
            adresse_livraison='Rue 1', ville='Lokossa', montant_total=10000, statut='payee',
        )

    def test_dates_remplies_au_changement_de_statut(self):
        self.assertIsNotNone(self.commande.payee_le)
        self.commande.statut = 'expediee'
        self.commande.save()
        self.commande.refresh_from_db()
        self.assertIsNotNone(self.commande.expediee_le)
        self.assertEqual(self.commande.progression, 67)
        etapes = self.commande.etapes_suivi()
        self.assertEqual([e['faite'] for e in etapes], [True, True, True, False])
        self.assertEqual([e['actuelle'] for e in etapes], [False, False, True, False])

    def test_page_de_suivi_reservee_au_proprietaire(self):
        url = reverse('boutique:suivi_commande', args=[self.commande.pk])
        self.client.force_login(self.client_kc)
        self.assertContains(self.client.get(url), 'Paiement reçu')
        self.client.force_login(User.objects.create_user('autre', password='pw-autre-123'))
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_action_admin_previent_le_client(self):
        admin_user = User.objects.create_superuser('chef', 'chef@example.com', 'pw-chef-12345')
        self.client.force_login(admin_user)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin_user.id
        session.save()
        url = reverse('admin:boutique_commande_changelist')
        self.client.post(url, {'action': 'marquer_expediee', '_selected_action': [self.commande.pk]})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'expediee')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('en route', mail.outbox[0].subject)
        self.assertIn(f'/boutique/commande/{self.commande.pk}/suivi/', mail.outbox[0].body)

    def test_commande_impayee_ne_bouge_pas(self):
        self.commande.statut = 'en_attente'
        self.commande.save()
        admin_user = User.objects.create_superuser('chef', 'chef@example.com', 'pw-chef-12345')
        self.client.force_login(admin_user)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin_user.id
        session.save()
        self.client.post(reverse('admin:boutique_commande_changelist'), {'action': 'marquer_livree', '_selected_action': [self.commande.pk]})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'en_attente')
        self.assertEqual(len(mail.outbox), 0)


class EchecEmailSuiviTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('chef2', 'chef2@example.com', 'pw-chef-12345')
        self.client.force_login(self.admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = self.admin.id
        session.save()
        self.commande = Commande.objects.create(
            utilisateur=self.admin, nom='K', prenom='A', email='a@example.com', telephone='1',
            adresse_livraison='r', ville='Lokossa', montant_total=1000, statut='payee',
        )

    def test_mot_de_passe_gmail_refuse_explique_dans_admin(self):
        import smtplib
        with patch('boutique.suivi.EmailMultiAlternatives.send', side_effect=smtplib.SMTPServerDisconnected('Connection unexpectedly closed')):
            reponse = self.client.post(reverse('admin:boutique_commande_changelist'),
                                       {'action': 'marquer_expediee', '_selected_action': [self.commande.pk]}, follow=True)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'expediee')          # le statut est quand même enregistré
        self.assertContains(reponse, 'mot de passe d&#x27;application')


class RechercheBoutiqueTests(TestCase):
    def setUp(self):
        from boutique.models import CategorieProduit
        capteurs = CategorieProduit.objects.create(nom='Capteurs', slug='capteurs')
        Produit.objects.create(nom='ESP32 DevKit', slug='esp32-r', description_courte='Wi-Fi', description='x', prix=1, stock=1)
        Produit.objects.create(nom='DHT22', slug='dht22-r', description_courte='Température et humidité', description='x', prix=1, stock=1, categorie=capteurs)

    def test_recherche_sans_rechargement_renvoie_seulement_les_resultats(self):
        reponse = self.client.get(reverse('boutique:liste'), {'q': 'humidité'}, HTTP_HX_REQUEST='true')
        html = reponse.content.decode()
        self.assertIn('DHT22', html)
        self.assertNotIn('ESP32 DevKit', html)
        self.assertNotIn('<html', html)                       # pas la page complète
        self.assertIn('id="flt-compte"', html)                # compteur mis à jour hors du bloc
        self.assertIn('hx-swap-oob="true"', html)
        self.assertIn('HX-Request', reponse['Vary'])

    def test_recherche_par_categorie_et_page_complete_sans_htmx(self):
        reponse = self.client.get(reverse('boutique:liste'), {'q': 'capteurs'})
        self.assertContains(reponse, 'DHT22')
        self.assertContains(reponse, '<html')

    def test_aucun_resultat_propose_whatsapp(self):
        reponse = self.client.get(reverse('boutique:liste'), {'q': 'lidar'}, HTTP_HX_REQUEST='true')
        self.assertContains(reponse, 'Aucun composant trouvé')
        self.assertContains(reponse, 'Demander sur WhatsApp')

    def test_adresse_propre_dans_le_navigateur(self):
        reponse = self.client.get(reverse('boutique:liste'), {'q': 'esp', 'categorie': ''}, HTTP_HX_REQUEST='true')
        self.assertEqual(reponse['HX-Push-Url'], '/boutique/?q=esp')


class CatalogueProduitsTests(TestCase):
    def setUp(self):
        from boutique.models import CategorieProduit
        electronique = CategorieProduit.objects.create(nom='Electronique', slug='electronique')
        Produit.objects.create(categorie=electronique, nom='ESP32', description_courte='x', description='x', prix=7000, stock=4)
        Produit.objects.create(categorie=electronique, nom='Relay 5V', description_courte='x', description='x', prix=800, stock=10)
        self.admin = User.objects.create_superuser('admin', 'admin@x.com', 'mdp')

    def test_catalogue_masque_stock_zero_sans_doublon(self):
        from boutique.catalogue import charger_catalogue, nombre_produits
        crees, _, inchangees = charger_catalogue()
        self.assertEqual((crees, inchangees), (nombre_produits() - 2, 2))
        self.assertEqual(Produit.objects.count(), nombre_produits())
        arduino = Produit.objects.get(slug='arduino-uno-r3')
        self.assertEqual((arduino.prix, arduino.stock, arduino.actif, arduino.categorie.slug), (6500, 0, False, 'electronique'))
        self.assertIn('Caractéristiques :\n• ', arduino.description)
        self.assertEqual(Produit.objects.get(slug='pompe-12v-4200-lh').categorie.nom, 'Électricité')
        # produits existants conservés tels quels (prix, stock, publication)
        esp32, relais = Produit.objects.get(slug='esp32'), Produit.objects.get(slug='relay-5v')
        self.assertEqual((esp32.prix, esp32.stock, esp32.actif), (7000, 4, True))
        self.assertEqual((relais.prix, relais.stock), (800, 10))
        self.assertFalse(Produit.objects.filter(slug='relais-5v').exists())
        self.assertEqual(charger_catalogue()[0], 0)

    def test_bouton_admin(self):
        self.client.force_login(self.admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = self.admin.pk
        session.save()
        self.assertContains(self.client.get(reverse('admin:boutique_produit_changelist')), 'Charger le catalogue de composants')
        reponse = self.client.post(reverse('admin:boutique_produit_charger_catalogue'))
        self.assertRedirects(reponse, reverse('admin:boutique_produit_changelist') + '?actif__exact=0')
        self.assertTrue(Produit.objects.filter(slug='monnayeur-electronique-ch-926', stock=0, actif=False).exists())
