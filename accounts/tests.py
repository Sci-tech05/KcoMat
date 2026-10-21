import re

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


MOT_DE_PASSE = 'Kc0mat-Secret!42'


class InscriptionTests(TestCase):
    def test_email_obligatoire_et_enregistre(self):
        reponse = self.client.post(reverse('accounts:inscription'), {
            'username': 'ama', 'email': 'Ama@Example.com',
            'password1': MOT_DE_PASSE, 'password2': MOT_DE_PASSE,
        })
        self.assertRedirects(reponse, reverse('accounts:dashboard'), fetch_redirect_response=False)
        self.assertEqual(User.objects.get(username='ama').email, 'ama@example.com')

    def test_email_deja_utilise_refuse(self):
        User.objects.create_user('kofi', 'kofi@example.com', MOT_DE_PASSE)
        reponse = self.client.post(reverse('accounts:inscription'), {
            'username': 'kofi2', 'email': 'KOFI@example.com',
            'password1': MOT_DE_PASSE, 'password2': MOT_DE_PASSE,
        })
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(User.objects.filter(username='kofi2').exists())

    def test_sans_email_refuse(self):
        reponse = self.client.post(reverse('accounts:inscription'), {
            'username': 'sansmail', 'password1': MOT_DE_PASSE, 'password2': MOT_DE_PASSE,
        })
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(User.objects.filter(username='sansmail').exists())


class ConnexionTests(TestCase):
    def setUp(self):
        User.objects.create_user('yao', 'yao@example.com', MOT_DE_PASSE)

    def test_connexion_par_email(self):
        reponse = self.client.post(reverse('accounts:connexion'), {'username': 'YAO@example.com', 'password': MOT_DE_PASSE})
        self.assertRedirects(reponse, reverse('accounts:dashboard'), fetch_redirect_response=False)

    def test_redirection_next_interne_conservee(self):
        url = reverse('accounts:connexion') + '?next=/boutique/panier/'
        reponse = self.client.post(url, {'username': 'yao', 'password': MOT_DE_PASSE})
        self.assertRedirects(reponse, '/boutique/panier/', fetch_redirect_response=False)

    def test_redirection_vers_site_externe_bloquee(self):
        for piege in ('https://site-pirate.com/', '//site-pirate.com/', 'http:/\\site-pirate.com'):
            self.client.logout()
            url = reverse('accounts:connexion') + '?next=' + piege
            reponse = self.client.post(url, {'username': 'yao', 'password': MOT_DE_PASSE})
            self.assertRedirects(reponse, reverse('accounts:dashboard'), fetch_redirect_response=False)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class MotDePasseOublieTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('afi', 'afi@example.com', 'ancien-MotDePasse-1')

    def test_parcours_complet(self):
        reponse = self.client.post(reverse('accounts:mdp_oublie'), {'email': 'afi@example.com'})
        self.assertRedirects(reponse, reverse('accounts:mdp_oublie_envoye'))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn('nouveau mot de passe', message.subject)
        self.assertTrue(message.alternatives, "l'e-mail doit avoir une version HTML")

        lien = re.search(r'https?://[^/]+(/accounts/mot-de-passe/nouveau/\S+/)', message.body).group(1)
        reponse = self.client.get(lien, follow=True)          # Django remplace le jeton par « set-password »
        self.assertContains(reponse, 'Choisissez un nouveau mot de passe')
        reponse = self.client.post(reponse.redirect_chain[-1][0], {
            'new_password1': MOT_DE_PASSE, 'new_password2': MOT_DE_PASSE,
        })
        self.assertRedirects(reponse, reverse('accounts:mdp_modifie'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(MOT_DE_PASSE))

    def test_email_inconnu_meme_reponse_sans_envoi(self):
        reponse = self.client.post(reverse('accounts:mdp_oublie'), {'email': 'inconnu@example.com'})
        self.assertRedirects(reponse, reverse('accounts:mdp_oublie_envoye'))
        self.assertEqual(len(mail.outbox), 0)

    def test_lien_invalide(self):
        reponse = self.client.get(reverse('accounts:mdp_nouveau', args=['MQ', 'jeton-faux']))
        self.assertContains(reponse, 'Lien expiré ou déjà utilisé')


class ProfilEmailTests(TestCase):
    def test_email_deja_pris_refuse(self):
        User.objects.create_user('a', 'pris@example.com', MOT_DE_PASSE)
        b = User.objects.create_user('b', '', MOT_DE_PASSE)
        self.client.force_login(b)
        self.client.post(reverse('accounts:profil'), {'action': 'profile', 'email': 'pris@example.com', 'first_name': '', 'last_name': ''})
        b.refresh_from_db()
        self.assertEqual(b.email, '')


class AntiEssaisTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        User.objects.create_user('kwame', 'kwame@example.com', MOT_DE_PASSE)

    def test_blocage_apres_cinq_echecs(self):
        url = reverse('accounts:connexion')
        for _ in range(5):
            self.client.post(url, {'username': 'kwame', 'password': 'mauvais'})
        # même le bon mot de passe est refusé pendant la pause
        reponse = self.client.post(url, {'username': 'kwame', 'password': MOT_DE_PASSE})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'Trop de tentatives')
        self.assertNotIn('_auth_user_id', self.client.session)


class DeconnexionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('esi', 'esi@example.com', MOT_DE_PASSE)
        self.client.force_login(self.user)

    def test_un_simple_lien_ne_deconnecte_pas(self):
        reponse = self.client.get(reverse('accounts:deconnexion'))
        self.assertContains(reponse, 'Se déconnecter ?')
        self.assertIn('_auth_user_id', self.client.session)

    def test_formulaire_deconnecte(self):
        reponse = self.client.post(reverse('accounts:deconnexion'))
        self.assertRedirects(reponse, reverse('core:accueil'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
