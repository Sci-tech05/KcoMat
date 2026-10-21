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


class PartageTests(TestCase):
    def test_image_apercu_1200x630_jpeg(self):
        import shutil, tempfile
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from core.templatetags.kcomat_tags import og_image
        dossier = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=dossier):
                tampon = BytesIO()
                Image.new('RGBA', (900, 900), (10, 132, 255, 128)).save(tampon, 'PNG')
                f = Formation.objects.create(titre='Drone', description_courte='Vol', description='x', prix=1000,
                                             image=SimpleUploadedFile('drone.png', tampon.getvalue(), 'image/png'))
                url = og_image(f.image)
                self.assertTrue(url.endswith('/cache/og/formations/drone.jpg'), url)
                with Image.open(f'{dossier}/cache/og/formations/drone.jpg') as img:
                    self.assertEqual((img.format, img.size), ('JPEG', (1200, 630)))
        finally:
            shutil.rmtree(dossier, ignore_errors=True)

    def test_boutons_de_partage_sur_formation(self):
        f = Formation.objects.create(titre='Domotique', description_courte='Maison connectée', description='x', prix=1000)
        html = self.client.get(reverse('formations:detail', args=[f.slug])).content.decode()
        for attendu in ('wa.me/?text=Domotique', 'facebook.com/sharer/sharer.php', 'linkedin.com/sharing', 'data-partage-copier'):
            self.assertIn(attendu, html)


from django.core import mail
from django.test import override_settings


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotificationsAdminTests(TestCase):
    """Chaque demande ou paiement d'un client envoie un e-mail pro à l'admin principal."""
    ADMIN = 'kcomat0@gmail.com'

    def mail_admin(self):
        envoyes = [m for m in mail.outbox if self.ADMIN in m.to]
        self.assertEqual(len(envoyes), 1, [m.subject for m in mail.outbox])
        m = envoyes[0]
        self.assertTrue(m.alternatives, "version HTML attendue")
        return m

    def test_message_de_contact(self):
        self.client.post(reverse('core:contact'), {'nom': 'Ama', 'email': 'ama@example.com', 'telephone': '0100',
                                                   'sujet': 'Devis', 'message': 'Bonjour'})
        m = self.mail_admin()
        self.assertIn('Nouveau message : Devis', m.subject)
        self.assertEqual(m.reply_to, ['ama@example.com'])
        self.assertIn('/core/contactmessage/', m.alternatives[0][0])   # bouton vers l'admin

    def test_demande_de_service(self):
        from services.models import Service
        s = Service.objects.create(titre='Installation solaire', description_courte='x', description='x')
        self.client.post(reverse('services:detail', args=[s.slug]), {'nom': 'Kofi', 'email': 'k@example.com', 'telephone': '01',
                                                                    'localite': 'Lokossa', 'description_besoin': 'Panneaux'})
        self.assertIn('Demande de devis : Installation solaire', self.mail_admin().subject)

    def test_demande_de_partenariat(self):
        self.client.post(reverse('partenariats:index'), {'nom_organisation': 'ONG Test', 'email': 'ong@example.com', 'telephone': '01'})
        self.assertIn('Demande de partenariat : ONG Test', self.mail_admin().subject)

    def test_inscription_confirmee_puis_formation_payee(self):
        from formations.views import _mark_inscription_formation_paid, _mark_inscription_frais_paid
        f = Formation.objects.create(titre='Domotique', description_courte='x', description='x', prix=20000)
        i = Inscription.objects.create(formation=f, nom='Doe', prenom='Jane', email='jane@example.com', telephone='01')
        _mark_inscription_frais_paid(i)
        m = self.mail_admin()
        self.assertIn('Nouvelle inscription : Domotique', m.subject)
        self.assertIn('2 000 FCFA', m.body)
        mail.outbox.clear()
        _mark_inscription_formation_paid(i)
        m = self.mail_admin()
        self.assertIn('Formation payée : Domotique', m.subject)
        self.assertIn('20 000 FCFA', m.body)

    def test_commande_payee(self):
        from boutique.views import _mark_commande_paid
        p = Produit.objects.create(nom='ESP32', slug='esp32-n', description_courte='x', description='x', prix=10000, stock=5)
        c = Commande.objects.create(nom='Doe', prenom='Jane', email='jane@example.com', telephone='01',
                                    adresse_livraison='Rue 1', ville='Lokossa', montant_total=20000)
        CommandeItem.objects.create(commande=c, produit=p, nom_produit='ESP32', prix_unitaire=10000, quantite=2)
        _mark_commande_paid(c)
        m = self.mail_admin()
        self.assertIn(f'Commande payée #{c.pk}', m.subject)
        self.assertIn('2 × ESP32', m.body)

    def test_echec_d_envoi_ne_bloque_pas_le_client(self):
        from unittest.mock import patch
        from .models import ContactMessage
        with patch('core.notifications_admin.EmailMultiAlternatives.send', side_effect=OSError('SMTP indisponible')):
            reponse = self.client.post(reverse('core:contact'), {'nom': 'Ama', 'email': 'ama@example.com',
                                                                 'sujet': 'Test', 'message': 'Bonjour'})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(ContactMessage.objects.filter(sujet='Test').exists())
