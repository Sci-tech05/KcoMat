import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from carrieres.catalogue import charger_catalogue
from carrieres.models import Offre
from formations.models import CategorieFormation, Formation
from partenariats.models import Partenaire

from .models import AbonnementPush, NotificationPush

SUB = {'endpoint': 'https://fcm.googleapis.com/fcm/send/abc123', 'keys': {'p256dh': 'cle-p256dh', 'auth': 'cle-auth'}}
PUSH_SETTINGS = dict(VAPID_PUBLIC_KEY='cle-publique', VAPID_PRIVATE_KEY='cle-privee', PUSH_ASYNC=False)


def abonner(**prefs):
    return AbonnementPush.objects.create(endpoint=f"https://fcm.googleapis.com/fcm/send/{AbonnementPush.objects.count()}",
                                         p256dh='p', auth='a', **prefs)


@override_settings(**PUSH_SETTINGS)
class AbonnementViewsTests(TestCase):
    def post(self, name, data, client=None):
        return (client or self.client).post(reverse(name), json.dumps(data), content_type='application/json')

    def test_abonnement_cree_puis_met_a_jour(self):
        r = self.post('notifications:abonnement', {'subscription': SUB, 'preferences': {'offres': True, 'formations': False, 'projets': True}})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['cree'])
        a = AbonnementPush.objects.get()
        self.assertEqual((a.offres, a.formations, a.projets), (True, False, True))
        self.post('notifications:abonnement', {'subscription': SUB, 'preferences': {'offres': False, 'formations': True, 'projets': True}})
        self.assertEqual(AbonnementPush.objects.count(), 1)
        a.refresh_from_db()
        self.assertEqual((a.offres, a.formations), (False, True))

    def test_abonnement_lie_au_compte(self):
        user = User.objects.create_user('awa', password='pw-awa-12345')
        self.client.force_login(user)
        self.post('notifications:abonnement', {'subscription': SUB})
        self.assertEqual(AbonnementPush.objects.get().utilisateur, user)

    def test_validation(self):
        mauvais = {'endpoint': 'http://pas-https.example', 'keys': {'p256dh': 'x', 'auth': 'y'}}
        self.assertEqual(self.post('notifications:abonnement', {'subscription': mauvais}).status_code, 400)
        aucun = {'subscription': SUB, 'preferences': {'offres': False, 'formations': False, 'projets': False}}
        self.assertEqual(self.post('notifications:abonnement', aucun).status_code, 400)
        self.assertEqual(self.client.post(reverse('notifications:abonnement'), 'pas du json', content_type='application/json').status_code, 400)
        self.assertEqual(AbonnementPush.objects.count(), 0)

    def test_csrf_obligatoire(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(self.post('notifications:abonnement', {'subscription': SUB}, client=client).status_code, 403)

    def test_desabonnement(self):
        self.post('notifications:abonnement', {'subscription': SUB})
        self.post('notifications:desabonnement', {'endpoint': SUB['endpoint']})
        self.assertFalse(AbonnementPush.objects.exists())

    def test_renouvellement_uniquement_pour_un_abonnement_existant(self):
        nouveau = {'endpoint': 'https://fcm.googleapis.com/fcm/send/nouveau', 'keys': {'p256dh': 'n', 'auth': 'n'}}
        client = Client(enforce_csrf_checks=True)   # appelé par le service worker, sans jeton
        r = client.post(reverse('notifications:renouvellement'), json.dumps({'ancien': 'https://inconnu', 'subscription': nouveau}),
                        content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(AbonnementPush.objects.exists())
        AbonnementPush.objects.create(endpoint=SUB['endpoint'], p256dh='p', auth='a', formations=False)
        client.post(reverse('notifications:renouvellement'), json.dumps({'ancien': SUB['endpoint'], 'subscription': nouveau}),
                    content_type='application/json')
        a = AbonnementPush.objects.get()
        self.assertEqual(a.endpoint, nouveau['endpoint'])
        self.assertFalse(a.formations)   # préférences conservées

    def test_service_worker_et_manifeste(self):
        r = self.client.get('/sw.js')
        self.assertEqual(r['Service-Worker-Allowed'], '/')
        self.assertIn('application/javascript', r['Content-Type'])
        self.assertContains(r, "addEventListener('push'")
        manifest = json.loads(self.client.get('/manifest.webmanifest').content)
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(len(manifest['icons']), 3)


@override_settings(**PUSH_SETTINGS)
@patch('pywebpush.webpush')
class PublicationTests(TestCase):
    def setUp(self):
        self.categorie = CategorieFormation.objects.create(nom='Domotique')

    def creer_formation(self, **extra):
        data = dict(titre='Arduino avancé', categorie=self.categorie, description_courte='Programmez des cartes Arduino.',
                    description='...', prix=25000)
        data.update(extra)
        with self.captureOnCommitCallbacks(execute=True):
            return Formation.objects.create(**data)

    def test_nouvelle_formation_notifie_les_abonnes_concernes(self, webpush):
        abonner(formations=True)
        abonner(formations=False)
        self.creer_formation()
        notification = NotificationPush.objects.get()
        self.assertEqual(notification.type_notification, 'formation')
        self.assertIn('Arduino avancé', notification.titre)
        self.assertEqual(notification.envoyes, 1)
        payload = json.loads(webpush.call_args.kwargs['data'])
        self.assertEqual(payload['url'], reverse('formations:detail', args=['arduino-avance']))
        self.assertIn('25 000 FCFA', payload['body'])

    def test_formation_masquee_puis_publiee_une_seule_annonce(self, webpush):
        abonner()
        formation = self.creer_formation(actif=False)
        self.assertFalse(NotificationPush.objects.exists())
        formation.actif = True
        with self.captureOnCommitCallbacks(execute=True):
            formation.save()
        formation.titre = 'Arduino avancé (mise à jour)'
        with self.captureOnCommitCallbacks(execute=True):
            formation.save()           # simple modification : pas de nouvelle annonce
        self.assertEqual(NotificationPush.objects.count(), 1)

    def test_catalogue_masque_et_offre_cloturee_ne_notifient_pas(self, webpush):
        abonner()
        with self.captureOnCommitCallbacks(execute=True):
            charger_catalogue()
        self.assertFalse(NotificationPush.objects.exists())
        offre = Offre.objects.get(slug='stage-domotique')
        offre.image = 'offres/test.jpg'
        offre.actif = True
        offre.date_limite = timezone.localdate() - timedelta(days=1)
        with self.captureOnCommitCallbacks(execute=True):
            offre.save()
        self.assertFalse(NotificationPush.objects.exists())

    def test_publication_groupee_admin_notifie(self, webpush):
        abonner()
        with self.captureOnCommitCallbacks(execute=True):
            charger_catalogue()
        offre = Offre.objects.get(slug='stage-domotique')
        offre.image = 'offres/test.jpg'
        offre.save()
        admin_user = User.objects.create_superuser('chef', 'chef@example.com', 'pw-chef-12345')
        self.client.force_login(admin_user)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin_user.pk
        session.save()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('admin:carrieres_offre_changelist'), {'action': 'publier', '_selected_action': [offre.pk]})
        notification = NotificationPush.objects.get()
        self.assertEqual(notification.type_notification, 'offre')
        self.assertIn('Nouveau stage', notification.titre)
        self.assertIn('20 000 FCFA', notification.message)

    def test_abonnement_expire_supprime(self, webpush):
        from pywebpush import WebPushException
        abonner()
        webpush.side_effect = WebPushException('gone', response=MagicMock(status_code=410))
        self.creer_formation()
        self.assertFalse(AbonnementPush.objects.exists())
        self.assertEqual(NotificationPush.objects.get().expires, 1)

    def test_echecs_repetes_desactivent(self, webpush):
        from pywebpush import WebPushException
        from .push import ECHECS_MAX, envoyer
        a = abonner()
        webpush.side_effect = WebPushException('erreur', response=MagicMock(status_code=500))
        for _ in range(ECHECS_MAX):
            envoyer(NotificationPush.objects.create(type_notification='annonce', titre='t', message='m'))
        a.refresh_from_db()
        self.assertFalse(a.actif)


class InscriptionEtPartenairesTests(TestCase):
    def test_creation_de_compte_propose_les_notifications(self):
        response = self.client.post(reverse('accounts:inscription'), {
            'username': 'nouveau', 'email': 'nouveau@example.com',
            'password1': 'Kcomat-Test-2026!', 'password2': 'Kcomat-Test-2026!'}, follow=True)
        self.assertContains(response, 'data-auto-open="1"')
        # proposé une seule fois
        self.assertContains(self.client.get(reverse('accounts:dashboard')), 'data-auto-open="0"')

    def test_bouton_sabonner_present(self):
        response = self.client.get('/')
        self.assertContains(response, 'data-push-open')
        self.assertContains(response, '/manifest.webmanifest')

    def test_partenaires_footer_et_contact(self):
        Partenaire.objects.create(nom='Partenaire Actif', site_web='https://exemple.bj')
        Partenaire.objects.create(nom='Partenaire Masqué', actif=False)
        for url in ('/', reverse('core:contact')):
            response = self.client.get(url)
            self.assertContains(response, 'Partenaire Actif')
            self.assertNotContains(response, 'Partenaire Masqué')
        self.assertContains(self.client.get(reverse('core:contact')), 'Nos partenaires')
