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

    def test_boutons_de_partage_sur_projet(self):
        from projets.models import Projet
        p = Projet.objects.create(titre='Robot', description_courte='Robot suiveur', description='x', actif=True)
        html = self.client.get(reverse('projets:detail', args=[p.slug])).content.decode()
        for attendu in ('wa.me/?text=Robot', 'facebook.com/sharer/sharer.php', 'linkedin.com/sharing', 'data-partage-copier'):
            self.assertIn(attendu, html)

    def test_admin_sans_comptes_sociaux(self):
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
        from django.contrib import admin
        for modele in (SocialApp, SocialAccount, SocialToken):
            self.assertFalse(admin.site.is_registered(modele))
        self.assertTrue(admin.site.is_registered(EmailAddress))


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


class CompressionImagesTests(TestCase):
    """Images envoyées compressées en WebP (original jamais conservé) + commande pour les images existantes."""

    def setUp(self):
        import tempfile
        self.media = tempfile.mkdtemp()
        self.reglage = override_settings(MEDIA_ROOT=self.media)
        self.reglage.enable()

    def tearDown(self):
        import shutil
        self.reglage.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    @staticmethod
    def fichier(nom, taille=(3000, 2000), mode='RGB', format_='JPEG'):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        tampon = BytesIO()
        Image.new(mode, taille, (200, 30, 30, 0) if mode == 'RGBA' else (200, 30, 30)).save(tampon, format_)
        return SimpleUploadedFile(nom, tampon.getvalue())

    def test_image_envoyee_compressee_sans_original(self):
        import os
        from PIL import Image
        from services.models import Service
        service = Service.objects.create(titre='Domotique', description_courte='x', description='x',
                                         image=self.fichier('photo-telephone.jpg'))
        self.assertTrue(service.image.name.endswith('.webp'), service.image.name)
        with Image.open(service.image.path) as img:
            self.assertEqual((img.format, max(img.size)), ('WEBP', 1600))
        self.assertEqual(os.listdir(os.path.join(self.media, 'services')), [os.path.basename(service.image.name)])

    def test_logo_partenaire_garde_sa_transparence(self):
        from PIL import Image
        from partenariats.models import Partenaire
        partenaire = Partenaire.objects.create(nom='EEJ', logo=self.fichier('logo.png', (900, 300), 'RGBA', 'PNG'))
        with Image.open(partenaire.logo.path) as img:
            self.assertEqual((img.mode, max(img.size)), ('RGBA', 600))

    def test_commande_simulation_puis_application(self):
        import os
        from io import StringIO
        from django.core.management import call_command
        from django.core.files.storage import default_storage
        from services.models import Service
        nom = default_storage.save('services/ancienne.jpg', self.fichier('ancienne.jpg'))
        service = Service.objects.create(titre='Ancien', description_courte='x', description='x')
        Service.objects.filter(pk=service.pk).update(image=nom)       # image déjà en ligne, non compressée

        call_command('compresser_images', stdout=StringIO())
        service.refresh_from_db()
        self.assertEqual(service.image.name, nom)                      # simulation : rien ne change

        sortie = StringIO()
        call_command('compresser_images', '--appliquer', stdout=sortie)
        service.refresh_from_db()
        self.assertEqual(service.image.name, 'services/ancienne.webp')
        self.assertFalse(os.path.exists(os.path.join(self.media, nom)))  # original supprimé
        self.assertIn('1 image(s)', sortie.getvalue())
        call_command('compresser_images', '--appliquer', stdout=sortie)  # relancer ne refait rien
        self.assertEqual(Service.objects.get(pk=service.pk).image.name, 'services/ancienne.webp')

    def test_ancienne_image_supprimee_si_remplacee_effacee_ou_element_supprime(self):
        import os
        from services.models import Service
        chemin = lambda nom: os.path.join(self.media, nom)
        with self.captureOnCommitCallbacks(execute=True):
            service = Service.objects.create(titre='A', description_courte='x', description='x', image=self.fichier('a.jpg', (400, 300)))
        premiere = service.image.name

        with self.captureOnCommitCallbacks(execute=True):            # remplacement
            service.image = self.fichier('b.jpg', (400, 300))
            service.save()
        self.assertFalse(os.path.exists(chemin(premiere)))
        seconde = service.image.name
        self.assertTrue(os.path.exists(chemin(seconde)))

        with self.captureOnCommitCallbacks(execute=True):            # case « Effacer »
            service.image = None
            service.save()
        self.assertFalse(os.path.exists(chemin(seconde)))

        with self.captureOnCommitCallbacks(execute=True):            # suppression de l'élément
            service.image = self.fichier('c.jpg', (400, 300))
            service.save()
        troisieme = service.image.name
        with self.captureOnCommitCallbacks(execute=True):
            service.delete()
        self.assertFalse(os.path.exists(chemin(troisieme)))

    def test_image_partagee_jamais_supprimee(self):
        import os
        from services.models import Service
        with self.captureOnCommitCallbacks(execute=True):
            a = Service.objects.create(titre='A', description_courte='x', description='x', image=self.fichier('a.jpg', (400, 300)))
            b = Service.objects.create(titre='B', description_courte='x', description='x')
        Service.objects.filter(pk=b.pk).update(image=a.image.name)
        with self.captureOnCommitCallbacks(execute=True):
            a.delete()
        self.assertTrue(os.path.exists(os.path.join(self.media, a.image.name)))


class PagesLegalesTests(TestCase):
    def test_politique_de_confidentialite(self):
        from django.urls import reverse
        r = self.client.get(reverse('core:confidentialite'))
        self.assertContains(r, 'Code du numérique')
        self.assertContains(r, 'FedaPay')
        self.assertContains(r, 'id="cookies"')
        self.assertContains(r, 'href="#droits"')
        self.assertContains(r, 'APDP')
        self.assertContains(r, reverse('core:mentions_legales'))

    def test_mentions_legales(self):
        from django.conf import settings
        from django.test import override_settings
        from django.urls import reverse
        r = self.client.get(reverse('core:mentions_legales'))
        self.assertContains(r, settings.KCOMAT_INFO['rccm'])
        self.assertContains(r, settings.KCOMAT_INFO['ifu'])
        self.assertContains(r, 'PythonAnywhere LLP')
        self.assertContains(r, 'Établissement (entreprise individuelle)')
        self.assertContains(r, 'La Direction de')
        with override_settings(KCOMAT_INFO={**settings.KCOMAT_INFO, 'directeur_publication': 'Prénom NOM'}):
            self.assertContains(self.client.get(reverse('core:mentions_legales')), 'Prénom NOM')

    def test_liens_dans_le_pied_de_page_et_le_sitemap(self):
        from django.urls import reverse
        accueil = self.client.get('/')
        self.assertContains(accueil, reverse('core:mentions_legales'))
        self.assertContains(accueil, reverse('core:confidentialite'))
        self.assertContains(self.client.get('/sitemap.xml'), reverse('core:mentions_legales'))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RelancesPaiementTests(TestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        from formations.models import Formation, Inscription
        self.maintenant = timezone.now()
        self.jours = lambda n: self.maintenant - timedelta(days=n)
        self.formation = Formation.objects.create(titre='Arduino', description_courte='c', description='d', prix=40000)
        self.insc = Inscription.objects.create(formation=self.formation, nom='DOSSOU', prenom='Awa', email='awa@example.com',
                                               telephone='0196000000')
        Inscription.objects.filter(pk=self.insc.pk).update(created_at=self.jours(4))

    def relancer(self, decalage_jours=0):
        from datetime import timedelta
        from core.relances import envoyer_relances
        mail.outbox.clear()
        return envoyer_relances(self.maintenant + timedelta(days=decalage_jours))

    def test_tous_les_3_jours_puis_lien_signe_utilisable(self):
        from unittest.mock import patch
        self.assertEqual(self.relancer(), 1)
        message = mail.outbox[0]
        self.assertIn('Finalisez votre inscription', message.subject)
        self.assertEqual(self.relancer(), 0)               # déjà relancé : rien avant 3 jours
        self.assertEqual(self.relancer(2), 0)
        self.assertEqual(self.relancer(3), 1)
        lien = next(l for l in message.body.split() if 'acces=' in l)
        chemin = lien.split('kcomat0.pythonanywhere.com', 1)[-1] if 'kcomat0' in lien else lien[lien.index('/formations'):]
        self.client.logout()
        with patch('formations.views.create_fedapay_transaction',
                   return_value={'success': True, 'transaction_id': 9, 'token': 't', 'checkout_url': 'https://x/t'}):
            self.assertEqual(self.client.get(chemin).status_code, 200)
            self.assertEqual(self.client.get(chemin.split('?')[0]).status_code, 200)  # accès mémorisé en session
        autre = self.client_class()
        self.assertEqual(autre.get(chemin.split('?')[0]).status_code, 403)          # sans jeton : refusé
        self.assertEqual(autre.get(chemin.split('?')[0] + '?acces=faux').status_code, 403)

    def test_vieille_inscription_abandonnee_jamais_relancee(self):
        from formations.models import Inscription
        Inscription.objects.filter(pk=self.insc.pk).update(created_at=self.jours(60))
        self.assertEqual(self.relancer(), 0)

    def test_plafond_puis_nouvelle_etape(self):
        from formations.models import Inscription
        Inscription.objects.filter(pk=self.insc.pk).update(relances_paiement=10, derniere_relance_le=self.jours(3))
        self.assertEqual(self.relancer(), 0)                # 10 relances : plafond atteint
        Inscription.objects.filter(pk=self.insc.pk).update(statut='frais_payes', frais_payes_le=self.jours(2.5))
        self.assertEqual(self.relancer(), 0)                # étape toute récente
        self.assertEqual(self.relancer(1), 1)               # 3 jours après le paiement des frais
        self.assertIn('Réglez votre formation', mail.outbox[0].subject)
        self.insc.refresh_from_db()
        self.assertEqual(self.insc.relances_paiement, 1)    # compteur repart pour la nouvelle étape

    def test_solde_boutique_et_consultation(self):
        from boutique.models import Commande
        from services.models import ACCOMPAGNEMENT_SLUG, DemandeService, Service
        from formations.models import Inscription
        Inscription.objects.all().delete()
        commande = Commande.objects.create(nom='D', prenom='Ali', email='ali@example.com', telephone='01',
                                           adresse_livraison='r', ville='Lokossa', montant_total=10000,
                                           mode_paiement='deux_tranches', statut='payee')
        Commande.objects.filter(pk=commande.pk).update(payee_le=self.jours(3))
        demande = DemandeService.objects.create(service=Service.objects.get(slug=ACCOMPAGNEMENT_SLUG), nom='Kofi',
                                                email='kofi@example.com', telephone='01', localite='L',
                                                intitule_projet='Serre', description_besoin='x')
        DemandeService.objects.filter(pk=demande.pk).update(created_at=self.jours(3))
        self.assertEqual(self.relancer(), 2)
        sujets = sorted(m.subject for m in mail.outbox)
        self.assertIn('Solde de votre commande', sujets[0])
        self.assertIn('Serre', sujets[1])

    def test_attestation_webinaire_chaque_semaine(self):
        from django.contrib.auth.models import User
        from webinaires.models import ParticipationWebinaire, Webinaire
        from formations.models import Inscription
        Inscription.objects.all().delete()
        user = User.objects.create_user('ami', 'ami@example.com', 'pw-ami-12345')
        w = Webinaire.objects.create(titre='ESP32', accroche='a', description='d', date_debut=self.jours(4),
                                     date_fin=self.jours(4) + timezone_heure(), prix_attestation=1000)
        ParticipationWebinaire.objects.create(webinaire=w, utilisateur=user, prenom='Ami', nom='K',
                                              email='ami@example.com', rejoint_le=self.jours(4))
        self.assertEqual(self.relancer(), 0)                # 4 jours seulement après la séance
        self.assertEqual(self.relancer(4), 1)
        self.assertIn('Votre attestation', mail.outbox[0].subject)
        self.assertEqual(self.relancer(8), 0)               # la suivante, une semaine après
        self.assertEqual(self.relancer(11), 1)


def timezone_heure():
    from datetime import timedelta
    return timedelta(hours=2)

from datetime import timedelta

from django.utils import timezone


class ALaUneEtCarrouselsTests(TestCase):
    def test_formations_produits_projets_a_la_une_en_premier(self):
        from boutique.models import Produit
        from formations.models import Formation
        from projets.models import Projet
        Formation.objects.create(titre='AAA classique', description_courte='c', description='d', prix=1, ordre=1)
        Formation.objects.create(titre='ZZZ à la une', description_courte='c', description='d', prix=1, ordre=99,
                                 en_vedette=True)
        Produit.objects.create(nom='AAA résistance', description_courte='x', description='x', prix=100)
        Produit.objects.create(nom='ZZZ capteur', description_courte='x', description='x', prix=100, en_vedette=True)
        Projet.objects.create(titre='Projet récent', description_courte='x', description='x')
        Projet.objects.create(titre='Projet phare', description_courte='x', description='x', en_vedette=True)
        Projet.objects.filter(titre='Projet phare').update(created_at=timezone.now() - timedelta(days=30))

        def avant(page, premier, second):
            contenu = page.content.decode()
            self.assertLess(contenu.index(premier), contenu.index(second))

        avant(self.client.get(reverse('formations:liste')), 'ZZZ à la une', 'AAA classique')
        avant(self.client.get(reverse('boutique:liste')), 'ZZZ capteur', 'AAA résistance')
        avant(self.client.get(reverse('projets:liste')), 'Projet phare', 'Projet récent')
        accueil = self.client.get('/')
        avant(accueil, 'ZZZ à la une', 'AAA classique')

    def test_carrousels_offres_puis_webinaires_a_1_5_s(self):
        from carrieres.models import Offre
        from webinaires.models import Webinaire
        debut = timezone.now() + timedelta(days=2)
        Webinaire.objects.create(titre='Webinaire ESP32', accroche='a', description='d', date_debut=debut,
                                 date_fin=debut + timedelta(hours=2), actif=True)
        Offre.objects.create(titre='Stage classique', type_offre='stage', domaine='iot', description='d',
                             competences_requises='c')
        Offre.objects.create(titre='Stage vedette', type_offre='stage', domaine='iot', description='d',
                             competences_requises='c', mise_en_avant=True)
        Offre.objects.create(titre='Offre close', type_offre='stage', domaine='iot', description='d',
                             competences_requises='c', date_limite=timezone.localdate() - timedelta(days=1))
        contenu = self.client.get('/').content.decode()
        self.assertIn('id="offres-track"', contenu)
        self.assertIn('id="webinaires-track"', contenu)
        self.assertLess(contenu.index('id="offres-track"'), contenu.index('id="webinaires-track"'))
        for piste in ('offres-track', 'webinaires-track'):
            balise = contenu[contenu.index(f'id="{piste}"'):].split('>', 1)[0]
            self.assertIn('data-intervalle="1500"', balise)
        self.assertLess(contenu.index('Stage vedette'), contenu.index('Stage classique'))
        self.assertNotIn('Offre close', contenu)
