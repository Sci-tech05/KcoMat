import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import DemandePartenariat, Partenaire

MEDIA = tempfile.mkdtemp()


def logo_png():
    tampon = BytesIO()
    Image.new('RGBA', (900, 300), (10, 132, 255, 0)).save(tampon, 'PNG')
    return SimpleUploadedFile('logo-acme.png', tampon.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIA, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class DemandePartenariatTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def envoyer(self, **extra):
        data = {'nom_organisation': 'Acme Bénin', 'email': 'contact@acme.bj', 'telephone': '0196000000',
                'site_web': 'https://acme.bj', 'type_partenariat_souhaite': 'Sponsoring', 'logo': logo_png()}
        data.update(extra)
        return self.client.post(reverse('partenariats:index'), data)

    def test_formulaire_avec_logo(self):
        self.assertContains(self.client.get(reverse('partenariats:index')), 'enctype="multipart/form-data"')
        self.assertEqual(self.envoyer().status_code, 302)
        demande = DemandePartenariat.objects.get()
        self.assertTrue(demande.logo.name.endswith('.webp'))
        self.assertFalse(Partenaire.objects.exists())      # pas encore traitée : rien sur le site

    def test_demande_traitee_apparait_aussitot_sur_le_site(self):
        self.envoyer()
        demande = DemandePartenariat.objects.get()
        demande.traite = True
        demande.save()
        partenaire = Partenaire.objects.get()
        self.assertEqual((partenaire.nom, partenaire.site_web, partenaire.actif), ('Acme Bénin', 'https://acme.bj', True))
        self.assertTrue(partenaire.logo)
        self.assertNotEqual(partenaire.logo.name, demande.logo.name)   # copie indépendante
        self.assertContains(self.client.get(reverse('partenariats:index')), 'Acme Bénin')
        # enregistrée à nouveau : pas de doublon ; décochée : masquée ; recochée : réaffichée
        demande.save()
        self.assertEqual(Partenaire.objects.count(), 1)
        demande.traite = False
        demande.save()
        self.assertFalse(Partenaire.objects.get().actif)
        demande.traite = True
        demande.save()
        self.assertTrue(Partenaire.objects.get().actif)
        self.assertEqual(Partenaire.objects.count(), 1)

    def test_case_traitee_dans_la_liste_admin(self):
        self.envoyer(logo='')
        demande = DemandePartenariat.objects.get()
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'pw-admin-12345')
        self.client.force_login(admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin.pk
        session.save()
        self.client.post(reverse('admin:partenariats_demandepartenariat_changelist'), {
            'action': 'accepter', '_selected_action': [demande.pk]})
        self.assertTrue(Partenaire.objects.get(nom='Acme Bénin').actif)
