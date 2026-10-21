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


class InscriptionUniqueTests(TestCase):
    """Une seule inscription en cours par personne et par formation ; reprise du paiement."""

    def setUp(self):
        self.formation = Formation.objects.create(titre='Domotique', description_courte='IoT', description='IoT', prix=20000)
        self.user = User.objects.create_user('awa', email='awa@example.com', password='pw-awa-123')
        self.url = reverse('formations:detail', args=[self.formation.slug])
        self.data = {'prenom': 'Awa', 'nom': 'Dossou', 'email': 'awa@example.com', 'telephone': '0197000000',
                     'mode_preference': 'presentiel'}

    def test_deuxieme_inscription_redirigee_vers_le_paiement_en_cours(self):
        self.client.force_login(self.user)
        r1 = self.client.post(self.url, self.data)
        inscription = Inscription.objects.get()
        self.assertRedirects(r1, reverse('formations:paiement_frais', args=[inscription.pk]), fetch_redirect_response=False)
        r2 = self.client.post(self.url, self.data)
        self.assertEqual(Inscription.objects.count(), 1)
        self.assertRedirects(r2, reverse('formations:paiement_frais', args=[inscription.pk]), fetch_redirect_response=False)
        # frais réglés : on est envoyé au paiement de la formation
        Inscription.objects.filter(pk=inscription.pk).update(statut='frais_payes')
        r3 = self.client.post(self.url, self.data)
        self.assertRedirects(r3, reverse('formations:paiement_formation', args=[inscription.pk]), fetch_redirect_response=False)
        page = self.client.get(self.url).content.decode()
        self.assertIn('Vous êtes déjà inscrit(e)', page)
        self.assertIn(reverse('formations:paiement_formation', args=[inscription.pk]), page)

    def test_meme_email_par_un_inconnu_refuse(self):
        Inscription.objects.create(formation=self.formation, utilisateur=self.user, nom='Dossou', prenom='Awa',
                                   email='awa@example.com', telephone='0197000000')
        r = self.client.post(self.url, {**self.data, 'email': 'AWA@example.com'})   # anonyme, même e-mail
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'déjà en cours pour cette adresse e-mail')
        self.assertEqual(Inscription.objects.count(), 1)

    def test_reinscription_possible_apres_formation_terminee_ou_annulee(self):
        self.client.force_login(self.user)
        for statut in ('termine', 'annule'):
            Inscription.objects.all().delete()
            Inscription.objects.create(formation=self.formation, utilisateur=self.user, nom='Dossou', prenom='Awa',
                                       email='awa@example.com', telephone='0197000000', statut=statut)
            self.client.post(self.url, self.data)
            self.assertEqual(Inscription.objects.filter(statut='en_attente').count(), 1, statut)

    def test_profil_propose_de_continuer_les_paiements(self):
        from boutique.models import Commande
        insc = Inscription.objects.create(formation=self.formation, utilisateur=self.user, nom='Dossou', prenom='Awa',
                                          email='awa@example.com', telephone='0197000000', statut='frais_payes')
        commande = Commande.objects.create(utilisateur=self.user, nom='D', prenom='A', email='awa@example.com',
                                           telephone='0197000000', adresse_livraison='x', ville='Lokossa', montant_total=5000)
        self.client.force_login(self.user)
        page = self.client.get(reverse('accounts:dashboard')).content.decode()
        self.assertIn(reverse('formations:paiement_formation', args=[insc.pk]), page)
        self.assertIn(reverse('boutique:paiement', args=[commande.pk]), page)
        self.assertIn('Continuer le paiement', page)


class OrdreAffichageTests(TestCase):
    def test_page_formations_suit_la_colonne_ordre(self):
        for titre, ordre in (('Zèbre', 10), ('Alpha', 30), ('Milieu', 20)):
            Formation.objects.create(titre=titre, description_courte='x', description='x', prix=1000, ordre=ordre)
        html = self.client.get(reverse('formations:liste')).content.decode()
        positions = [html.index(f'>{t}<') if f'>{t}<' in html else html.index(t) for t in ('Zèbre', 'Milieu', 'Alpha')]
        self.assertEqual(positions, sorted(positions))
