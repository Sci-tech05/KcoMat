import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from notifications.models import AbonnementPush, NotificationPush

from .catalogue import CATALOGUE, charger_catalogue
from .models import ParticipationWebinaire, Webinaire
from .rappels import envoyer_rappels_dus, verifier_rappels

PUSH = dict(VAPID_PUBLIC_KEY='cle-publique', VAPID_PRIVATE_KEY='cle-privee', PUSH_ASYNC=False,
            JITSI_BASE_URL='https://framatalk.org', EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')


def creer_webinaire(debut_dans, duree=90, **extra):
    debut = timezone.now() + debut_dans
    data = dict(titre='Introduction à l’ESP32', accroche='Découvrir l’ESP32.', description='Paragraphe un.\n\nParagraphe deux.',
                points_cles='Un\nDeux', date_debut=debut, date_fin=debut + timedelta(minutes=duree), actif=True)
    data.update(extra)
    return Webinaire.objects.create(**data)


@override_settings(**PUSH)
class CalendrierTests(TestCase):
    def test_statuts_et_ouverture_de_salle(self):
        w = creer_webinaire(timedelta(hours=2))
        debut = w.date_debut
        self.assertEqual(w.statut(debut - timedelta(minutes=11)), 'a_venir')
        self.assertFalse(w.salle_ouverte(debut - timedelta(minutes=11)))
        self.assertEqual(w.statut(debut - timedelta(minutes=10)), 'ouvert')
        self.assertTrue(w.salle_ouverte(debut - timedelta(minutes=10)))
        self.assertEqual(w.statut(debut + timedelta(minutes=5)), 'en_direct')
        self.assertEqual(w.statut(w.date_fin), 'termine')
        self.assertTrue(w.salle_ouverte(w.date_fin + timedelta(minutes=29)))
        self.assertFalse(w.salle_ouverte(w.date_fin + timedelta(minutes=31)))
        self.assertEqual(w.duree, '1 h 30')
        self.assertTrue(w.salle_jitsi.startswith('kcomat-webinaire-'))

    def test_slug_unique(self):
        a, b = creer_webinaire(timedelta(days=1)), creer_webinaire(timedelta(days=2))
        self.assertNotEqual(a.slug, b.slug)


@override_settings(**PUSH)
@patch('pywebpush.webpush')
class ParcoursTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('awa', 'awa@example.com', 'pw-awa-12345')

    def test_accueil_affiche_le_webinaire_et_le_bouton_participer_a_10_min(self, webpush):
        w = creer_webinaire(timedelta(days=3))
        r = self.client.get('/')
        self.assertContains(r, w.titre)
        self.assertContains(r, 'Réserver ma place')
        self.assertNotContains(r, reverse('webinaires:salle', args=[w.slug]))
        w.date_debut = timezone.now() + timedelta(minutes=9)
        w.date_fin = w.date_debut + timedelta(hours=1)
        w.save()
        r = self.client.get('/')
        self.assertContains(r, reverse('webinaires:salle', args=[w.slug]))
        self.assertContains(r, 'Participer')

    def test_masque_et_termine_absents_de_l_accueil(self, webpush):
        creer_webinaire(timedelta(days=1), titre='Masqué', actif=False)
        creer_webinaire(-timedelta(days=1), titre='Déjà passé')
        r = self.client.get('/')
        self.assertNotContains(r, 'Masqué')
        self.assertNotContains(r, 'id="webinaires"')

    def test_inscription_compte_obligatoire_puis_confirmation(self, webpush):
        w = creer_webinaire(timedelta(days=2))
        url = reverse('webinaires:inscrire', args=[w.slug])
        self.assertEqual(self.client.post(url, {'prenom': 'Awa', 'nom': 'Dossou'}).status_code, 302)
        self.assertFalse(ParticipationWebinaire.objects.exists())
        self.client.force_login(self.user)
        self.client.post(url, {'prenom': ' awa ', 'nom': 'dossou'})
        self.client.post(url, {'prenom': 'Awa', 'nom': 'Dossou'})   # double clic
        p = ParticipationWebinaire.objects.get()
        self.assertEqual((p.prenom, p.nom, p.email), ('Awa', 'DOSSOU', 'awa@example.com'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].attachments[0][2], 'text/calendar')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Awa')
        self.assertContains(self.client.get(reverse('webinaires:detail', args=[w.slug])), 'Votre place est réservée')

    def test_places_limitees(self, webpush):
        w = creer_webinaire(timedelta(days=2), places=1)
        autre = User.objects.create_user('kofi', 'kofi@example.com', 'pw-kofi-12345')
        ParticipationWebinaire.objects.create(webinaire=w, utilisateur=autre, prenom='K', nom='K', email='k@example.com')
        self.client.force_login(self.user)
        self.client.post(reverse('webinaires:inscrire', args=[w.slug]), {'prenom': 'Awa', 'nom': 'Dossou'})
        self.assertEqual(w.participations.count(), 1)

    def test_salle_fermee_avant_10_min_puis_presence_enregistree(self, webpush):
        w = creer_webinaire(timedelta(hours=1))
        self.client.force_login(self.user)
        salle = reverse('webinaires:salle', args=[w.slug])
        self.assertRedirects(self.client.get(salle), reverse('webinaires:detail', args=[w.slug]))
        w.date_debut = timezone.now() + timedelta(minutes=5)
        w.date_fin = w.date_debut + timedelta(hours=1)
        w.save()
        # sans nom sur le compte : passage par le formulaire (nom de l'attestation)
        self.assertEqual(self.client.get(salle).status_code, 302)
        self.user.first_name, self.user.last_name = 'Awa', 'Dossou'
        self.user.save()
        r = self.client.get(salle)
        self.assertContains(r, 'framatalk.org/external_api.js')
        self.assertContains(r, w.salle_jitsi)
        self.assertIsNotNone(ParticipationWebinaire.objects.get(webinaire=w, utilisateur=self.user).rejoint_le)

    def test_attestation_pour_les_presents_apres_la_fin(self, webpush):
        w = creer_webinaire(timedelta(minutes=5))
        p = ParticipationWebinaire.objects.create(webinaire=w, utilisateur=self.user, prenom='Awa', nom='DOSSOU',
                                                  email='awa@example.com')
        self.client.force_login(self.user)
        url = reverse('webinaires:attestation', args=[w.slug])
        self.assertEqual(self.client.get(url).status_code, 302)      # pas encore terminé
        Webinaire.objects.filter(pk=w.pk).update(date_debut=timezone.now() - timedelta(hours=2),
                                                 date_fin=timezone.now() - timedelta(minutes=30))
        self.assertEqual(self.client.get(url).status_code, 302)      # absent
        ParticipationWebinaire.objects.filter(pk=p.pk).update(rejoint_le=timezone.now() - timedelta(hours=1))
        r = self.client.get(url)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))
        self.assertIn('attachment', r['Content-Disposition'])
        verif = self.client.get(reverse('webinaires:verifier', args=[p.code_verification]))
        self.assertContains(verif, 'Attestation authentique')
        self.assertContains(verif, 'Awa DOSSOU')
        self.assertEqual(self.client.get(reverse('webinaires:verifier', args=['inconnu'])).status_code, 404)
        detail = self.client.get(reverse('webinaires:detail', args=[w.slug]))
        self.assertContains(detail, 'Télécharger mon attestation')

    def test_agenda_ics(self, webpush):
        w = creer_webinaire(timedelta(days=1))
        r = self.client.get(reverse('webinaires:agenda', args=[w.slug]))
        self.assertIn('text/calendar', r['Content-Type'])
        self.assertContains(r, 'BEGIN:VEVENT')
        self.assertContains(r, 'TRIGGER:-PT20M')


@override_settings(**PUSH)
@patch('pywebpush.webpush')
class NotificationsTests(TestCase):
    def setUp(self):
        cache.clear()

    def abonner(self, **prefs):
        return AbonnementPush.objects.create(endpoint=f"https://fcm.googleapis.com/fcm/send/{AbonnementPush.objects.count()}",
                                             p256dh='p', auth='a', **prefs)

    def test_publication_notifie_les_abonnes_webinaires(self, webpush):
        self.abonner(webinaires=True)
        self.abonner(webinaires=False)
        with self.captureOnCommitCallbacks(execute=True):
            w = creer_webinaire(timedelta(days=3))
        n = NotificationPush.objects.get(type_notification='webinaire')
        self.assertEqual(n.envoyes, 1)
        self.assertIn(w.titre, n.titre)
        payload = json.loads(webpush.call_args.kwargs['data'])
        self.assertEqual(payload['url'], reverse('webinaires:detail', args=[w.slug]))

    def test_rappel_20_min_avant_une_seule_fois(self, webpush):
        self.abonner()
        w = creer_webinaire(timedelta(minutes=45), actif=False)
        user = User.objects.create_user('awa', 'awa@example.com', 'pw')
        ParticipationWebinaire.objects.create(webinaire=w, utilisateur=user, prenom='Awa', nom='D', email='awa@example.com')
        Webinaire.objects.filter(pk=w.pk).update(actif=True)
        self.assertEqual(envoyer_rappels_dus(), [])               # 45 min avant : trop tôt
        maintenant = w.date_debut - timedelta(minutes=19)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(len(envoyer_rappels_dus(maintenant)), 1)
        self.assertEqual(envoyer_rappels_dus(maintenant), [])     # déjà envoyé
        self.assertEqual(NotificationPush.objects.filter(type_notification='webinaire_rappel').count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(reverse('webinaires:salle', args=[w.slug]), mail.outbox[0].body)

    def test_les_visites_declenchent_le_rappel(self, webpush):
        w = creer_webinaire(timedelta(minutes=15), actif=False)
        Webinaire.objects.filter(pk=w.pk).update(actif=True)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.get('/')
        w.refresh_from_db()
        self.assertIsNotNone(w.rappel_envoye_le)
        verifier_rappels()   # throttlé : aucune erreur, aucun doublon
        self.assertEqual(NotificationPush.objects.filter(type_notification='webinaire_rappel').count(), 1)

    def test_preference_webinaires_enregistree(self, webpush):
        sub = {'endpoint': 'https://fcm.googleapis.com/fcm/send/x', 'keys': {'p256dh': 'p', 'auth': 'a'}}
        self.client.post(reverse('notifications:abonnement'),
                         json.dumps({'subscription': sub, 'preferences': {'offres': False, 'formations': False,
                                                                          'projets': False, 'webinaires': True}}),
                         content_type='application/json')
        self.assertTrue(AbonnementPush.objects.get().webinaires)


class CatalogueEtAdminTests(TestCase):
    def test_catalogue_masque_sans_doublon(self):
        self.assertEqual(charger_catalogue(), (len(CATALOGUE), 0))
        self.assertEqual(charger_catalogue(), (0, len(CATALOGUE)))
        self.assertFalse(Webinaire.objects.filter(actif=True).exists())
        debuts = [timezone.localtime(w.date_debut) for w in Webinaire.objects.order_by('date_debut')]
        self.assertTrue(all(d.weekday() == 5 and d.hour == 20 for d in debuts))
        self.assertTrue(all(w.duree == '2 h' for w in Webinaire.objects.all()))

    def test_pages_admin(self):
        admin_user = User.objects.create_superuser('chef', 'chef@example.com', 'pw-chef-12345')
        self.client.force_login(admin_user)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin_user.pk
        session.save()
        w = creer_webinaire(-timedelta(hours=3))
        p = ParticipationWebinaire.objects.create(webinaire=w, utilisateur=admin_user, prenom='Chef', nom='KCO',
                                                  email='chef@example.com', rejoint_le=timezone.now())
        self.assertEqual(self.client.get(reverse('admin:webinaires_webinaire_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:webinaires_webinaire_change', args=[w.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:webinaires_participationwebinaire_changelist')).status_code, 200)
        pdf = self.client.get(reverse('admin:webinaires_participationwebinaire_attestation', args=[p.pk]))
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        # saisie : une date, une heure de début, une heure de fin
        ajout = self.client.post(reverse('admin:webinaires_webinaire_add'), {
            'titre': 'Algorithmique', 'slug': '', 'theme': 'algorithmique', 'accroche': 'Accroche.', 'description': 'Texte.',
            'points_cles': '', 'intervenant': 'KcoMat', 'intervenant_fonction': '', 'places': 0,
            'jour': (timezone.localdate() + timedelta(days=10)).strftime('%d/%m/%Y'),
            'heure_debut': '20:00', 'heure_fin': '22:00',
            'participations-TOTAL_FORMS': 0, 'participations-INITIAL_FORMS': 0,
            'participations-MIN_NUM_FORMS': 0, 'participations-MAX_NUM_FORMS': 1000,
        })
        self.assertEqual(ajout.status_code, 302, ajout.context and ajout.context['adminform'].form.errors)
        cree = Webinaire.objects.get(titre='Algorithmique')
        self.assertEqual((timezone.localtime(cree.date_debut).hour, timezone.localtime(cree.date_fin).hour), (20, 22))
        self.assertEqual(timezone.localtime(cree.date_debut).date(), timezone.localtime(cree.date_fin).date())
        self.assertContains(self.client.get(reverse('admin:webinaires_webinaire_change', args=[cree.pk])), 'value="20:00"')
        futur = creer_webinaire(timedelta(days=4))
        self.client.post(reverse('admin:webinaires_webinaire_changelist'),
                         {'action': 'mettre_horaire_soiree', '_selected_action': [futur.pk]})
        futur.refresh_from_db()
        debut, fin = timezone.localtime(futur.date_debut), timezone.localtime(futur.date_fin)
        self.assertEqual((debut.hour, fin.hour, debut.date()), (20, 22, fin.date()))
        csv = self.client.post(reverse('admin:webinaires_webinaire_changelist'),
                               {'action': 'exporter_participants', '_selected_action': [w.pk]})
        self.assertIn('Chef', csv.content.decode('utf-8'))
