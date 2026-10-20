import io
import shutil
import tempfile
import zipfile
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from carrieres.models import Candidature, Offre

TEMP_MEDIA = tempfile.mkdtemp(prefix='kcomat-test-media-')
PDF = b'%PDF-1.4\n% faux CV de test\n'


def fichier(nom='cv.pdf', contenu=PDF, type_mime='application/pdf'):
    return SimpleUploadedFile(nom, contenu, content_type=type_mime)


@override_settings(MEDIA_ROOT=TEMP_MEDIA, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CandidaturePubliqueTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.offre = Offre.objects.create(titre='Stage IoT', type_offre='stage', domaine='IoT',
                                          description='desc', competences_requises='ESP32')
        self.url = reverse('carrieres:detail', args=[self.offre.slug])

    def postuler(self, **extra):
        data = {'prenom': 'Awa', 'nom': 'Dossou', 'email': 'awa@example.com', 'telephone': '+229 01 97 00 00 00',
                'message': 'Je suis passionnée par l’IoT. ' * 15, 'cv': fichier()}
        data.update(extra)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, data)

    def test_candidature_notifie_equipe_et_candidat(self):
        response = self.postuler(lettre_motivation=fichier('lettre.pdf'))
        self.assertEqual(response.status_code, 302)
        candidature = Candidature.objects.get()
        self.assertEqual(candidature.statut, 'nouvelle')
        self.assertEqual(len(mail.outbox), 2)

        alerte, accuse = mail.outbox
        self.assertEqual(alerte.to, ['kcomat0@gmail.com'])
        self.assertEqual(alerte.reply_to, ['awa@example.com'])
        self.assertIn('Stage IoT', alerte.subject)
        self.assertIn(reverse('admin:carrieres_candidature_change', args=[candidature.pk]), alerte.body)
        self.assertEqual(sorted(a[0] for a in alerte.attachments), ['CV_DOSSOU_AWA.pdf', 'Lettre_DOSSOU_AWA.pdf'])
        self.assertEqual(accuse.to, ['awa@example.com'])

    def test_fichiers_nommes_de_facon_imprevisible(self):
        self.postuler()
        nom = Candidature.objects.get().cv.name
        self.assertTrue(nom.startswith('candidatures/cv/'))
        self.assertNotIn('cv.pdf', nom)

    def test_format_et_taille_refuses(self):
        self.postuler(cv=fichier('virus.exe', b'MZ', 'application/octet-stream'))
        self.postuler(cv=fichier('gros.pdf', b'0' * (5 * 1024 * 1024 + 1)))
        self.assertEqual(Candidature.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_echec_email_ne_perd_pas_la_candidature(self):
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend', EMAIL_HOST='127.0.0.1', EMAIL_PORT=1):
            response = self.postuler()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Candidature.objects.count(), 1)

    def test_pre_score(self):
        self.postuler(lettre_motivation=fichier('lettre.pdf'))
        self.assertEqual(Candidature.objects.get().score_auto, 100)
        Candidature.objects.all().delete()
        self.postuler(message='', telephone='123', cv=fichier('cv.docx', b'doc', 'application/octet-stream'))
        self.assertEqual(Candidature.objects.get().score_auto, 10 + 20)  # CV non PDF + dans les délais


@override_settings(MEDIA_ROOT=TEMP_MEDIA, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CandidatureAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('chef', 'chef@example.com', 'pw-chef-123')
        self.client.force_login(self.admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = self.admin.pk
        session.save()
        self.offre = Offre.objects.create(titre='Technicien', type_offre='emploi', domaine='Élec',
                                          description='d', competences_requises='c')
        self.retenue = Candidature.objects.create(offre=self.offre, nom='Agbo', prenom='Luc', email='luc@example.com',
                                                  telephone='0197000000', cv=fichier(), statut='retenue', note=5)
        self.refusee = Candidature.objects.create(offre=self.offre, nom='Houn', prenom='Eva', email='eva@example.com',
                                                  telephone='0197000001', cv=fichier(), statut='refusee')

    def test_statut_clos_synchronise_traite(self):
        self.assertTrue(self.retenue.traite)
        self.retenue.statut = 'en_revue'
        self.retenue.save()
        self.retenue.refresh_from_db()
        self.assertFalse(self.retenue.traite)
        self.assertIsNotNone(self.retenue.statut_modifie_le)

    def test_liste_avec_synthese_du_mois(self):
        response = self.client.get(reverse('admin:carrieres_candidature_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['mois_stats']['total'], 2)
        self.assertEqual(response.context['mois_stats']['retenues'], 1)

    def test_zip_des_retenus_du_mois(self):
        today = timezone.localdate()
        response = self.client.get(reverse('admin:carrieres_candidature_export_retenues'),
                                   {'year': today.year, 'month': today.month})
        self.assertEqual(response['Content-Type'], 'application/zip')
        noms = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
        self.assertIn('index_candidatures.csv', noms)
        self.assertTrue(any(n.startswith('Retenue/') and n.endswith('CV_AGBO_LUC.pdf') for n in noms))
        self.assertFalse(any('HOUN' in n for n in noms))

    def test_rapport_pdf(self):
        response = self.client.get(reverse('admin:carrieres_candidature_export_rapport'))
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_document_reserve_au_staff(self):
        url = reverse('admin:carrieres_candidature_document', args=[self.retenue.pk, 'cv'])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        self.assertNotEqual(self.client.get(url).status_code, 200)

    def test_action_reponse_email(self):
        self.client.post(reverse('admin:carrieres_candidature_changelist'), {
            'action': 'envoyer_reponses', '_selected_action': [self.retenue.pk, self.refusee.pk]})
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ['eva@example.com', 'luc@example.com'])
        self.retenue.refresh_from_db()
        self.assertIsNotNone(self.retenue.reponse_envoyee_le)

    def test_candidature_apres_date_limite_penalisee(self):
        self.offre.date_limite = timezone.localdate() - timedelta(days=1)
        self.offre.save()
        tardive = Candidature.objects.create(offre=self.offre, nom='T', prenom='T', email='t@example.com',
                                             telephone='0197000002', cv=fichier())
        self.assertEqual(dict((l, p) for l, p, _ in tardive.score_details())['Envoyée avant la date limite'], 0)


def image_offre():
    # GIF 1x1 valide : accepté par ImageField, et ignoré par la conversion WebP
    return SimpleUploadedFile('offre.gif', b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x00\x00\x00\x00\x00'
                                           b',\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;', content_type='image/gif')


@override_settings(MEDIA_ROOT=TEMP_MEDIA, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class OffresPremiumTests(TestCase):
    def setUp(self):
        from carrieres.catalogue import charger_catalogue
        self.crees, _, _ = charger_catalogue()
        self.stage = Offre.objects.get(slug='stage-domotique')

    def publier(self, offre, **extra):
        offre.image = image_offre()
        offre.actif = True
        for k, v in extra.items():
            setattr(offre, k, v)
        offre.save()
        return offre

    def test_catalogue_complet_masque_et_idempotent(self):
        from carrieres.catalogue import DOMAINES, charger_catalogue
        self.assertEqual(self.crees, len(DOMAINES) * 3)
        self.assertFalse(Offre.objects.filter(slug__in=['stage-domotique', 'emploi-ia', 'freelance-drones'], actif=True).exists())
        self.assertEqual([(f.duree, f.montant, f.recommandee) for f in self.stage.formules.all()],
                         [('1 mois', 20000, False), ('3 mois et plus', 50000, True)])
        self.assertEqual(charger_catalogue()[0], 0)
        self.assertEqual(Offre.objects.count(), len(DOMAINES) * 3)

    def test_publication_impossible_sans_image(self):
        from django.core.exceptions import ValidationError
        self.stage.actif = True
        with self.assertRaises(ValidationError):
            self.stage.full_clean()

    def test_action_publier_ignore_les_offres_sans_image(self):
        admin = User.objects.create_superuser('rh', 'rh@example.com', 'pw-rh-12345')
        self.client.force_login(admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin.pk
        session.save()
        avec_image = Offre.objects.get(slug='emploi-domotique')
        avec_image.image = image_offre()
        avec_image.save()
        self.client.post(reverse('admin:carrieres_offre_changelist'), {
            'action': 'publier', '_selected_action': [self.stage.pk, avec_image.pk]})
        self.stage.refresh_from_db()
        avec_image.refresh_from_db()
        self.assertFalse(self.stage.actif)
        self.assertTrue(avec_image.actif)

    def test_liste_filtre_et_formules(self):
        self.publier(self.stage, date_limite=timezone.localdate() + timedelta(days=5))
        self.publier(Offre.objects.get(slug='emploi-web-mobile'))
        response = self.client.get(reverse('carrieres:liste'), {'type': 'stage'})
        self.assertContains(response, 'Stagiaire technicien(ne) domotique')
        self.assertNotContains(response, 'Développeur(se) web &amp; mobile full-stack')
        self.assertContains(response, '20')
        self.assertContains(response, 'J-5')

    def test_candidature_avec_formule_obligatoire(self):
        self.publier(self.stage)
        url = reverse('carrieres:detail', args=[self.stage.slug])
        data = {'prenom': 'Awa', 'nom': 'Dossou', 'email': 'awa@example.com', 'telephone': '0197000000'}
        self.client.post(url, {**data, 'cv': fichier()})
        self.assertEqual(Candidature.objects.count(), 0)

        formule = self.stage.formules.get(recommandee=True)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(url, {**data, 'cv': fichier(), 'formule': formule.pk})
        candidature = Candidature.objects.get()
        self.assertEqual(candidature.formule, formule)
        self.assertIn('3 mois et plus', mail.outbox[0].body)

    def test_offre_cloturee_refuse_les_candidatures(self):
        self.publier(self.stage, date_limite=timezone.localdate() - timedelta(days=1))
        url = reverse('carrieres:detail', args=[self.stage.slug])
        self.assertContains(self.client.get(url), 'Les candidatures sont closes')
        self.client.post(url, {'prenom': 'A', 'nom': 'B', 'email': 'a@example.com', 'telephone': '0197000000',
                               'cv': fichier(), 'formule': self.stage.formules.first().pk})
        self.assertEqual(Candidature.objects.count(), 0)

    def test_fiche_job_posting(self):
        self.publier(self.stage)
        response = self.client.get(reverse('carrieres:detail', args=[self.stage.slug]))
        self.assertContains(response, '"@type": "JobPosting"')
        self.assertContains(response, '"employmentType": "INTERN"')
        self.assertContains(response, 'Vos missions')
        self.assertContains(response, 'Formule conseillée')
