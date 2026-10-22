from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from boutique.models import Commande, Produit

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


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SuiviCommandeTests(TestCase):
    def setUp(self):
        self.client_kc = User.objects.create_user('ama', 'ama@example.com', 'pw-ama-12345')
        self.commande = Commande.objects.create(
            utilisateur=self.client_kc, nom='Kossi', prenom='Ama', email='ama@example.com', telephone='1',
            adresse_livraison='Rue 1', ville='Lokossa', montant_total=10000, statut='payee',
        )

    def test_dates_remplies_au_changement_de_statut(self):
        self.assertIsNotNone(self.commande.payee_le)
        self.commande.statut = 'expediee'
        self.commande.save()
        self.commande.refresh_from_db()
        self.assertIsNotNone(self.commande.expediee_le)
        self.assertEqual(self.commande.progression, 67)
        etapes = self.commande.etapes_suivi()
        self.assertEqual([e['faite'] for e in etapes], [True, True, True, False])
        self.assertEqual([e['actuelle'] for e in etapes], [False, False, True, False])

    def test_page_de_suivi_reservee_au_proprietaire(self):
        url = reverse('boutique:suivi_commande', args=[self.commande.pk])
        self.client.force_login(self.client_kc)
        self.assertContains(self.client.get(url), 'Paiement reçu')
        self.client.force_login(User.objects.create_user('autre', password='pw-autre-123'))
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_action_admin_previent_le_client(self):
        admin_user = User.objects.create_superuser('chef', 'chef@example.com', 'pw-chef-12345')
        self.client.force_login(admin_user)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin_user.id
        session.save()
        url = reverse('admin:boutique_commande_changelist')
        self.client.post(url, {'action': 'marquer_expediee', '_selected_action': [self.commande.pk]})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'expediee')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('en route', mail.outbox[0].subject)
        self.assertIn(f'/boutique/commande/{self.commande.pk}/suivi/', mail.outbox[0].body)

    def test_commande_impayee_ne_bouge_pas(self):
        self.commande.statut = 'en_attente'
        self.commande.save()
        admin_user = User.objects.create_superuser('chef', 'chef@example.com', 'pw-chef-12345')
        self.client.force_login(admin_user)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin_user.id
        session.save()
        self.client.post(reverse('admin:boutique_commande_changelist'), {'action': 'marquer_livree', '_selected_action': [self.commande.pk]})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'en_attente')
        self.assertEqual(len(mail.outbox), 0)


class EchecEmailSuiviTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('chef2', 'chef2@example.com', 'pw-chef-12345')
        self.client.force_login(self.admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = self.admin.id
        session.save()
        self.commande = Commande.objects.create(
            utilisateur=self.admin, nom='K', prenom='A', email='a@example.com', telephone='1',
            adresse_livraison='r', ville='Lokossa', montant_total=1000, statut='payee',
        )

    def test_mot_de_passe_gmail_refuse_explique_dans_admin(self):
        import smtplib
        with patch('boutique.suivi.EmailMultiAlternatives.send', side_effect=smtplib.SMTPServerDisconnected('Connection unexpectedly closed')):
            reponse = self.client.post(reverse('admin:boutique_commande_changelist'),
                                       {'action': 'marquer_expediee', '_selected_action': [self.commande.pk]}, follow=True)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'expediee')          # le statut est quand même enregistré
        self.assertContains(reponse, 'mot de passe d&#x27;application')


class RechercheBoutiqueTests(TestCase):
    def setUp(self):
        from boutique.models import CategorieProduit
        capteurs = CategorieProduit.objects.create(nom='Capteurs', slug='capteurs')
        Produit.objects.create(nom='ESP32 DevKit', slug='esp32-r', description_courte='Wi-Fi', description='x', prix=1, stock=1)
        Produit.objects.create(nom='DHT22', slug='dht22-r', description_courte='Température et humidité', description='x', prix=1, stock=1, categorie=capteurs)

    def test_recherche_sans_rechargement_renvoie_seulement_les_resultats(self):
        reponse = self.client.get(reverse('boutique:liste'), {'q': 'humidité'}, HTTP_HX_REQUEST='true')
        html = reponse.content.decode()
        self.assertIn('DHT22', html)
        self.assertNotIn('ESP32 DevKit', html)
        self.assertNotIn('<html', html)                       # pas la page complète
        self.assertIn('id="flt-compte"', html)                # compteur mis à jour hors du bloc
        self.assertIn('hx-swap-oob="true"', html)
        self.assertIn('HX-Request', reponse['Vary'])

    def test_recherche_par_categorie_et_page_complete_sans_htmx(self):
        reponse = self.client.get(reverse('boutique:liste'), {'q': 'capteurs'})
        self.assertContains(reponse, 'DHT22')
        self.assertContains(reponse, '<html')

    def test_aucun_resultat_propose_whatsapp(self):
        reponse = self.client.get(reverse('boutique:liste'), {'q': 'lidar'}, HTTP_HX_REQUEST='true')
        self.assertContains(reponse, 'Aucun composant trouvé')
        self.assertContains(reponse, 'Demander sur WhatsApp')

    def test_adresse_propre_dans_le_navigateur(self):
        reponse = self.client.get(reverse('boutique:liste'), {'q': 'esp', 'categorie': ''}, HTTP_HX_REQUEST='true')
        self.assertEqual(reponse['HX-Push-Url'], '/boutique/?q=esp')


class CatalogueProduitsTests(TestCase):
    def setUp(self):
        from boutique.models import CategorieProduit
        electronique = CategorieProduit.objects.create(nom='Electronique', slug='electronique')
        Produit.objects.create(categorie=electronique, nom='ESP32', description_courte='x', description='x', prix=7000, stock=4)
        Produit.objects.create(categorie=electronique, nom='Relay 5V', description_courte='x', description='x', prix=800, stock=10)
        self.admin = User.objects.create_superuser('admin', 'admin@x.com', 'mdp')

    def test_catalogue_masque_stock_zero_sans_doublon(self):
        from boutique.catalogue import charger_catalogue, nombre_produits
        crees, _, inchangees = charger_catalogue()
        self.assertEqual((crees, inchangees), (nombre_produits() - 2, 14))  # ESP32, Relay 5V + DHT22, MQ-2, 3 LED, relais 5V, module 2 canaux, 220 Ω, ESP32 Wi-Fi, protoboard, jumpers M-M et M-F déjà au catalogue
        self.assertEqual(Produit.objects.count(), nombre_produits())
        arduino = Produit.objects.get(slug='arduino-uno-r3')
        self.assertEqual((arduino.prix, arduino.stock, arduino.actif, arduino.categorie.slug), (6500, 0, False, 'electronique'))
        self.assertIn('Caractéristiques :\n• ', arduino.description)
        self.assertEqual(Produit.objects.get(slug='pompe-12v-4200-lh').categorie.nom, 'Électricité')
        # produits existants conservés tels quels (prix, stock, publication)
        esp32, relais = Produit.objects.get(slug='esp32'), Produit.objects.get(slug='relay-5v')
        self.assertEqual((esp32.prix, esp32.stock, esp32.actif), (7000, 4, True))
        self.assertEqual((relais.prix, relais.stock), (800, 10))
        self.assertFalse(Produit.objects.filter(slug='relais-5v').exists())
        self.assertEqual(charger_catalogue()[0], 0)

    def test_capteurs_prix_majores_de_30_pourcent(self):
        from boutique.catalogue import charger_catalogue, prix_majore
        charger_catalogue()
        hcsr04 = Produit.objects.get(slug='capteur-a-ultrasons-hc-sr04')
        self.assertEqual((hcsr04.prix, hcsr04.stock, hcsr04.actif, hcsr04.categorie.slug), (2080, 0, False, 'capteurs'))
        self.assertEqual((prix_majore(600), prix_majore(35), prix_majore(4585), prix_majore(19.6)), (780, 50, 5965, 30))
        # LED : jamais moins de 50 FCFA (19,6 ou 25 FCFA chez la source)
        self.assertEqual(Produit.objects.get(slug='led-orange-3mm-transparente').prix, 50)
        self.assertEqual(Produit.objects.get(slug='led-rouge-10mm-transparente').prix, 75)
        self.assertEqual(Produit.objects.get(slug='encodeur-rotatif-ky-040').categorie.slug, 'boutons-interrupteurs')
        self.assertEqual(Produit.objects.get(slug='capuchon-bouton-poussoir-noir').prix, 50)
        ssr = Produit.objects.get(slug='relais-statique-ssr-40da')
        self.assertEqual((ssr.prix, ssr.categorie.slug), (3585, 'relais'))
        self.assertEqual(Produit.objects.get(slug='resistance-22k-1w').prix, 55)
        self.assertEqual(Produit.objects.get(slug='resistance-10k-1-4w').prix, 50)  # 20 FCFA + 30 % → minimum 50
        hc05 = Produit.objects.get(slug='module-bluetooth-hc-05')
        self.assertEqual((hc05.prix, hc05.categorie.slug), (5070, 'sans-fil'))
        self.assertFalse(Produit.objects.filter(slug='module-wifi-esp32').exists())  # = ESP32 existant
        self.assertEqual(Produit.objects.get(slug='module-gps-neo-6m').categorie.slug, 'gsm-gps')
        self.assertEqual(Produit.objects.get(slug='tresse-a-dessouder').prix, 730)
        prix = lambda slug: Produit.objects.get(slug=slug).prix
        self.assertEqual((prix('jumper-male-male-30cm'), prix('lot-40-jumpers-male-male-30cm'), prix('lot-40-jumpers-male-male-20cm')),
                         (50, 2000, 1820))  # jumpers alignés sur 50 FCFA l'unité
        self.assertEqual(prix('connecteur-male-2-broches'), 50)
        self.assertFalse(Produit.objects.filter(slug='resistance-220-ohms-1-4w').exists())  # = « Résistance 220 Ω » existante
        self.assertFalse(Produit.objects.filter(slug__in=['relais-5v-simple', 'module-relais-5v-2-canaux']).exists())
        oled = Produit.objects.get(slug='ecran-oled-091')
        self.assertEqual((oled.prix, oled.categorie.slug), (3185, 'leds-afficheurs'))
        # LED de base déjà vendues en Électronique : pas de doublon
        self.assertFalse(Produit.objects.filter(slug__in=['led-rouge-visible', 'led-verte-visible', 'led-bleu']).exists())
        # doublons des capteurs déjà vendus : on garde la fiche existante
        self.assertFalse(Produit.objects.filter(slug__in=['dht22-module', 'capteur-de-gaz-fumee-mq2']).exists())
        sg90 = Produit.objects.get(slug='micro-servomoteur-sg90-180')
        self.assertEqual((sg90.prix, sg90.stock, sg90.categorie.slug), (1755, 0, 'moteurs-robotique'))

    def test_slugs_du_catalogue_uniques_et_courts(self):
        from boutique.catalogue import PRODUITS, slug_produit
        slugs = [slug_produit(fiche) for fiches in PRODUITS.values() for fiche in fiches]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertLessEqual(max(map(len, slugs)), 50)

    def test_bouton_admin(self):
        self.client.force_login(self.admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = self.admin.pk
        session.save()
        self.assertContains(self.client.get(reverse('admin:boutique_produit_changelist')), 'Charger le catalogue de composants')
        reponse = self.client.post(reverse('admin:boutique_produit_charger_catalogue'))
        self.assertRedirects(reponse, reverse('admin:boutique_produit_changelist') + '?actif__exact=0')
        self.assertTrue(Produit.objects.filter(slug='monnayeur-electronique-ch-926', stock=0, actif=False).exists())


class VisuelEtImageParLienTests(TestCase):
    """Niveau 1 : visuel généré sans photo. Niveau 3 : image importée depuis un lien, compressée en WebP."""

    def setUp(self):
        import tempfile
        from boutique.models import CategorieProduit
        self.media = tempfile.mkdtemp()
        self.capteurs = CategorieProduit.objects.create(nom='Capteurs', slug='capteurs')
        self.produit = Produit.objects.create(categorie=self.capteurs, nom='Capteur à ultrasons HC-SR04', reference='HC-SR04',
                                              description_courte='x', description='x', prix=2080, stock=3)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.media, ignore_errors=True)

    @staticmethod
    def png(taille=(3000, 2000), mode='RGBA'):
        from io import BytesIO
        from PIL import Image
        tampon = BytesIO()
        Image.new(mode, taille, (10, 132, 255, 128) if mode == 'RGBA' else (10, 132, 255)).save(tampon, 'PNG')
        return tampon.getvalue()

    def test_visuel_genere_sans_photo(self):
        liste = self.client.get(reverse('boutique:liste')).content.decode()
        self.assertIn('kx-visuel kx-visuel--carte', liste)
        self.assertIn('--kx-visuel: #059669', liste)  # couleur de la catégorie Capteurs
        detail = self.client.get(reverse('boutique:detail', args=[self.produit.slug])).content.decode()
        self.assertIn('kx-visuel--grand', detail)
        self.assertIn('HC-SR04', detail)

    def test_compression_webp_1200px_fond_blanc(self):
        from io import BytesIO
        from PIL import Image
        from boutique.images import compresser
        fichier = compresser(BytesIO(self.png()))
        with Image.open(BytesIO(fichier.read())) as img:
            self.assertEqual((img.format, img.mode, max(img.size)), ('WEBP', 'RGB', 1200))
        self.assertLess(fichier.size, 200 * 1024)

    def test_lien_interne_ou_non_image_refuse(self):
        from django.core.exceptions import ValidationError
        from boutique.images import image_depuis_lien
        for lien in ('http://127.0.0.1/photo.png', 'http://192.168.1.1/photo.png', 'ftp://exemple.com/photo.png'):
            with self.assertRaises(ValidationError):
                image_depuis_lien(lien)

        class PageHtml:
            status_code, is_redirect, headers = 200, False, {'Content-Type': 'text/html'}

        with patch('boutique.images.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.215.14', 0))]), \
                patch('boutique.images.requests.get', return_value=PageHtml()):
            with self.assertRaisesMessage(ValidationError, "n'est pas une image"):
                image_depuis_lien('https://exemple.com/page')

    def test_admin_importe_l_image_du_lien(self):
        admin = User.objects.create_superuser('admin', 'admin@x.com', 'mdp')
        self.client.force_login(admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin.pk
        session.save()
        png = self.png()

        class ReponseImage:
            status_code, is_redirect, headers = 200, False, {'Content-Type': 'image/png'}

            def iter_content(self, taille):
                yield png

        donnees = {'categorie': self.capteurs.pk, 'nom': self.produit.nom, 'slug': self.produit.slug, 'reference': 'HC-SR04',
                   'description_courte': 'x', 'description': 'x', 'image_lien': 'https://exemple.com/hc-sr04.png',
                   'prix': 2080, 'stock': 3, 'actif': 'on',
                   'images-TOTAL_FORMS': 0, 'images-INITIAL_FORMS': 0, 'images-MIN_NUM_FORMS': 0, 'images-MAX_NUM_FORMS': 1000}
        with override_settings(MEDIA_ROOT=self.media), \
                patch('boutique.images.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.215.14', 0))]), \
                patch('boutique.images.requests.get', return_value=ReponseImage()):
            reponse = self.client.post(reverse('admin:boutique_produit_change', args=[self.produit.pk]), donnees)
            self.assertEqual(reponse.status_code, 302, reponse.content[:3000])
            self.produit.refresh_from_db()
            self.assertTrue(self.produit.image.name.endswith('.webp'), self.produit.image.name)
            self.assertLess(self.produit.image.size, 200 * 1024)


class StockEnMasseTests(TestCase):
    def setUp(self):
        for i in range(3):
            Produit.objects.create(nom=f'Composant {i}', description_courte='x', description='x', prix=100, stock=i)
        admin = User.objects.create_superuser('admin', 'admin@x.com', 'mdp')
        self.client.force_login(admin)
        session = self.client.session
        session['admin_2fa_verified_user_id'] = admin.pk
        session.save()

    def lancer(self, **donnees):
        return self.client.post(reverse('admin:boutique_produit_changelist'), {
            'action': 'definir_stock', 'index': 0, 'select_across': 1,
            '_selected_action': [p.pk for p in Produit.objects.all()], **donnees}, follow=True)

    def test_stock_de_tous_les_produits_a_la_quantite_saisie(self):
        reponse = self.lancer(quantite=25)
        self.assertEqual(set(Produit.objects.values_list('stock', flat=True)), {25})
        self.assertContains(reponse, 'Stock mis à 25 pour 3 produit(s).')

    def test_sans_quantite_rien_ne_change(self):
        reponse = self.lancer(quantite='')
        self.assertEqual(sorted(Produit.objects.values_list('stock', flat=True)), [0, 1, 2])
        self.assertContains(reponse, 'Saisissez la quantité')
        self.lancer(quantite=-4)
        self.assertEqual(sorted(Produit.objects.values_list('stock', flat=True)), [0, 1, 2])
