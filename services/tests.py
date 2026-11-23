from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import ACCOMPAGNEMENT_SLUG, DemandeService, Service


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccompagnementProjetTests(TestCase):
    def test_service_ajoute_par_la_migration(self):
        service = Service.objects.get(slug=ACCOMPAGNEMENT_SLUG)
        self.assertTrue(service.actif)
        self.assertContains(self.client.get(reverse('services:liste')), 'Accompagnement de projet')

    def test_page_affiche_la_procedure_et_la_fiche(self):
        r = self.client.get(reverse('services:detail', args=[ACCOMPAGNEMENT_SLUG]))
        self.assertContains(r, 'Session de consultation')
        self.assertContains(r, 'Acquisition des matériels')
        self.assertContains(r, 'Devis personnalisé')
        self.assertContains(r, 'kcomat-demande-accompagnement-projet.pdf')
        self.assertContains(r, 'name="intitule_projet"')
        self.assertNotContains(r, 'name="budget_estime"')
        self.assertNotContains(r, 'Devis gratuit')

    def test_demande_d_accompagnement(self):
        url = reverse('services:detail', args=[ACCOMPAGNEMENT_SLUG])
        data = {'nom': 'Awa Dossou', 'email': 'awa@example.com', 'telephone': '0196000000', 'localite': 'Lokossa',
                'structure': 'Université d’Abomey-Calavi', 'description_besoin': 'Arrosage automatique par ESP32.'}
        self.assertEqual(self.client.post(url, data).status_code, 200)     # intitulé obligatoire
        self.assertEqual(self.client.post(url, {**data, 'intitule_projet': 'Irrigation intelligente'}).status_code, 302)
        demande = DemandeService.objects.get()
        self.assertEqual((demande.intitule_projet, demande.structure), ('Irrigation intelligente', 'Université d’Abomey-Calavi'))
        self.assertEqual(mail.outbox, [])          # paiement obligatoire : rien n'est transmis avant le règlement

    def test_demande_non_payee_masquee_dans_l_admin(self):
        from django.contrib.auth.models import User
        service = Service.objects.get(slug=ACCOMPAGNEMENT_SLUG)
        commun = dict(service=service, email='a@example.com', telephone='01', localite='Lokossa', description_besoin='x')
        DemandeService.objects.create(nom='Payée', intitule_projet='Projet payé', consultation_payee_le=timezone.now(), **commun)
        DemandeService.objects.create(nom='Abandon', intitule_projet='Projet abandonné', **commun)
        admin = User.objects.create_superuser('chef', 'chef@example.com', 'pw-chef-12345')
        self.client.force_login(admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin.pk
        session.save()
        url = reverse('admin:services_demandeservice_changelist')
        r = self.client.get(url)
        self.assertContains(r, 'Projet payé')
        self.assertNotContains(r, 'Projet abandonné')
        self.assertContains(self.client.get(url + '?consultation=attente'), 'Projet abandonné')

    def test_autres_services_inchanges(self):
        autre = Service.objects.exclude(slug=ACCOMPAGNEMENT_SLUG).first()
        r = self.client.get(reverse('services:detail', args=[autre.slug]))
        self.assertContains(r, 'Devis gratuit')
        self.assertContains(r, 'name="budget_estime"')


FETCH = 'api.fedapay_service.fetch_fedapay_transaction'
CREATE = 'services.paiement.create_fedapay_transaction'


def transaction(tx_id, montant=2000, statut='approved', demande_id=None):
    data = {'id': tx_id, 'status': statut, 'amount': montant, 'currency': {'iso': 'XOF'}}
    if demande_id is not None:
        data['custom_metadata'] = {'type': 'consultation_accompagnement', 'demande_id': str(demande_id)}
    return data


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PaiementConsultationTests(TestCase):
    def envoyer_demande(self):
        from unittest.mock import patch
        url = reverse('services:detail', args=[ACCOMPAGNEMENT_SLUG])
        data = {'nom': 'DOSSOU Awa Mireille', 'email': 'awa@example.com', 'telephone': '0196000000', 'localite': 'Lokossa',
                'intitule_projet': 'Irrigation intelligente', 'description_besoin': 'Arrosage automatique.'}
        with patch(CREATE, return_value={'success': True, 'transaction_id': 501, 'token': 'tok',
                                         'checkout_url': 'https://checkout.fedapay.com/checkout/tok'}) as create:
            r = self.client.post(url, data, follow=True)
        self.demande = DemandeService.objects.get()
        return r, create

    def test_demande_puis_redirection_vers_fedapay(self):
        r, create = self.envoyer_demande()
        self.assertContains(r, 'https://checkout.fedapay.com/checkout/tok')
        payload = create.call_args.args[0]
        self.assertEqual(payload['amount'], 2000)
        self.assertEqual(payload['metadata']['type'], 'consultation_accompagnement')
        self.assertEqual(payload['metadata']['demande_id'], str(self.demande.pk))
        self.assertEqual((payload['customer']['lastname'], payload['customer']['firstname']), ('DOSSOU', 'Awa Mireille'))
        self.assertEqual(self.demande.fedapay_consultation_id, '501')

    def test_paiement_confirme_une_seule_fois(self):
        from unittest.mock import patch
        self.envoyer_demande()
        mail.outbox.clear()
        confirmation = reverse('services:confirmation_consultation', args=[self.demande.pk])
        with patch(FETCH, return_value=transaction(501, statut='pending')):
            r = self.client.get(confirmation)
        self.assertContains(r, 'Paiement de la consultation en attente')
        with patch(FETCH, return_value=transaction(501)):
            r = self.client.get(confirmation)
            self.client.get(reverse('services:callback_consultation', args=[self.demande.pk]))   # retour en double
        self.assertContains(r, 'Votre consultation est réglée')
        self.demande.refresh_from_db()
        self.assertTrue(self.demande.consultation_payee)
        facture = [m for m in mail.outbox if m.to == ['awa@example.com']]
        self.assertEqual(len(facture), 1)
        self.assertEqual(facture[0].attachments[0][2], 'application/pdf')
        self.assertTrue(self.client.get(reverse('services:facture_consultation', args=[self.demande.pk])).content.startswith(b'%PDF'))

    def test_montant_incorrect_refuse(self):
        from unittest.mock import patch
        self.envoyer_demande()
        with patch(FETCH, return_value=transaction(501, montant=200)):
            self.client.get(reverse('services:confirmation_consultation', args=[self.demande.pk]))
        self.demande.refresh_from_db()
        self.assertFalse(self.demande.consultation_payee)

    def test_webhook_avec_transaction_d_une_autre_demande_refuse(self):
        import json
        from unittest.mock import patch
        self.envoyer_demande()
        corps = json.dumps({'name': 'transaction.approved', 'data': {'transaction': {'id': 999}}})
        callback = reverse('services:callback_consultation', args=[self.demande.pk])
        autre = {'501': transaction(501, statut='pending'), '999': transaction(999, demande_id=self.demande.pk + 1)}
        with patch(FETCH, side_effect=lambda tx_id: autre.get(str(tx_id), {})):
            self.client.post(callback, corps, content_type='application/json')
        self.demande.refresh_from_db()
        self.assertFalse(self.demande.consultation_payee)
        bonne = {'501': transaction(501, statut='pending'), '999': transaction(999, demande_id=self.demande.pk)}
        with patch(FETCH, side_effect=lambda tx_id: bonne.get(str(tx_id), {})):
            self.client.post(callback, corps, content_type='application/json')
        self.demande.refresh_from_db()
        self.assertTrue(self.demande.consultation_payee)

    def test_demande_d_un_autre_visiteur_inaccessible(self):
        self.envoyer_demande()
        self.client.logout()
        self.client.cookies.clear()
        self.assertEqual(self.client.get(reverse('services:facture_consultation', args=[self.demande.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('services:paiement_consultation', args=[self.demande.pk])).status_code, 403)
