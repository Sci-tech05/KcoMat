from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from api.fedapay_service import verify_fedapay_payment
from formations.models import Formation, Inscription

FETCH = 'api.fedapay_service.fetch_fedapay_transaction'


def fake_transactions(transactions):
    """Simule GET /transactions/{id} : renvoie la transaction connue ou {}."""
    return lambda transaction_id: transactions.get(str(transaction_id), {})


def tx(tx_id, amount, status='approved', metadata=None):
    data = {'id': tx_id, 'status': status, 'amount': amount, 'currency': {'iso': 'XOF'}}
    if metadata is not None:
        data['custom_metadata'] = metadata
    return data


class VerifyFedapayPaymentTests(TestCase):
    def verify(self, transactions, stored, candidate=None, amount=2000, ref=1):
        with patch(FETCH, side_effect=fake_transactions(transactions)):
            return verify_fedapay_payment(
                stored_transaction_id=stored,
                candidate_transaction_id=candidate,
                expected_amount=amount,
                expected_type='inscription_frais',
                ref_key='inscription_id',
                expected_ref=ref,
            )

    def test_stored_transaction_approved_with_matching_metadata(self):
        txs = {'10': tx(10, 2000, metadata={'type': 'inscription_frais', 'inscription_id': '1'})}
        self.assertEqual(self.verify(txs, stored='10'), '10')

    def test_stored_transaction_without_metadata_is_accepted(self):
        self.assertEqual(self.verify({'10': tx(10, 2000)}, stored='10'), '10')

    def test_pending_transaction_is_rejected(self):
        self.assertIsNone(self.verify({'10': tx(10, 2000, status='pending')}, stored='10'))

    def test_wrong_amount_is_rejected(self):
        self.assertIsNone(self.verify({'10': tx(10, 100)}, stored='10'))

    def test_wrong_currency_is_rejected(self):
        data = tx(10, 2000)
        data['currency'] = {'iso': 'EUR'}
        self.assertIsNone(self.verify({'10': data}, stored='10'))

    def test_stored_transaction_with_foreign_metadata_is_rejected(self):
        txs = {'10': tx(10, 2000, metadata={'type': 'inscription_frais', 'inscription_id': '99'})}
        self.assertIsNone(self.verify(txs, stored='10'))

    def test_url_candidate_without_metadata_is_rejected(self):
        txs = {'10': tx(10, 2000, status='pending'), '77': tx(77, 2000)}
        self.assertIsNone(self.verify(txs, stored='10', candidate='77'))

    def test_url_candidate_for_another_object_is_rejected(self):
        txs = {'77': tx(77, 2000, metadata={'type': 'inscription_frais', 'inscription_id': '2'})}
        self.assertIsNone(self.verify(txs, stored='', candidate='77'))

    def test_url_candidate_of_another_type_is_rejected(self):
        txs = {'77': tx(77, 2000, metadata={'type': 'commande', 'inscription_id': '1'})}
        self.assertIsNone(self.verify(txs, stored='', candidate='77'))

    def test_url_candidate_bound_to_this_object_is_accepted(self):
        txs = {
            '10': tx(10, 2000, status='pending'),
            '77': tx(77, 2000, metadata={'type': 'inscription_frais', 'inscription_id': '1'}),
        }
        self.assertEqual(self.verify(txs, stored='10', candidate='77'), '77')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class InscriptionSecurityTests(TestCase):
    def setUp(self):
        self.formation = Formation.objects.create(
            titre='Domotique', description_courte='IoT', description='IoT', prix=20000,
        )
        self.owner = User.objects.create_user('owner', password='pw-owner-123')
        self.other = User.objects.create_user('other', password='pw-other-123')
        self.inscription = Inscription.objects.create(
            formation=self.formation, utilisateur=self.owner, nom='Doe', prenom='Jane',
            email='jane@example.com', telephone='0100000000', mode_preference='en_ligne',
            statut='frais_payes', fedapay_frais_id='10', fedapay_formation_id='20',
        )

    def test_cheap_frais_transaction_cannot_pay_the_formation(self):
        """Rejouer la transaction des frais (2 000 FCFA) via ?id= ne valide pas la formation."""
        txs = {
            '10': tx(10, 2000, metadata={'type': 'inscription_frais', 'inscription_id': str(self.inscription.pk)}),
            '20': tx(20, 20000, status='pending'),
        }
        self.client.force_login(self.owner)
        with patch(FETCH, side_effect=fake_transactions(txs)):
            self.client.get(reverse('formations:succes_formation', args=[self.inscription.pk]), {'id': '10'})
            self.client.get(reverse('formations:callback_formation', args=[self.inscription.pk]),
                            {'id': '10', 'status': 'approved'})
        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, 'frais_payes')

    def test_real_formation_payment_is_accepted(self):
        txs = {'20': tx(20, 20000, metadata={'type': 'inscription_formation',
                                             'inscription_id': str(self.inscription.pk)})}
        with patch(FETCH, side_effect=fake_transactions(txs)):
            self.client.get(reverse('formations:callback_formation', args=[self.inscription.pk]),
                            {'id': '20', 'status': 'approved'})
        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, 'complet')

    def test_other_user_cannot_read_invoice_or_success_page(self):
        self.client.force_login(self.other)
        for name in ('formations:facture_frais', 'formations:succes', 'formations:paiement_frais'):
            response = self.client.get(reverse(name, args=[self.inscription.pk]))
            self.assertEqual(response.status_code, 403, name)

    def test_anonymous_inscription_only_visible_from_its_session(self):
        anonymous = Inscription.objects.create(
            formation=self.formation, nom='Anon', prenom='A', email='a@example.com', telephone='0100000001',
        )
        url = reverse('formations:facture_frais', args=[anonymous.pk])
        self.assertEqual(self.client.get(url).status_code, 403)

        session = self.client.session
        session['kcomat_inscriptions'] = [anonymous.pk]
        session.save()
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_meet_room_requires_full_payment(self):
        self.client.force_login(self.owner)
        url = reverse('formations:meet_room', args=[self.inscription.pk])
        self.assertEqual(self.client.get(url).status_code, 403)

        self.inscription.statut = 'complet'
        self.inscription.save(update_fields=['statut'])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_meet_room_forbidden_to_other_user_even_if_paid(self):
        self.inscription.statut = 'complet'
        self.inscription.save(update_fields=['statut'])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('formations:meet_room', args=[self.inscription.pk])).status_code, 403)

    def test_open_transaction_api_is_removed(self):
        self.assertEqual(self.client.post('/api/create-transaction/').status_code, 404)
