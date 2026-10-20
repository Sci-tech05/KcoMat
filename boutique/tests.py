from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from boutique.models import Commande

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
