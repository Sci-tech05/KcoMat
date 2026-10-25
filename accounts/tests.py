import re

from django.conf import settings
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


# ---------------------------------------------------------------------------
# Connexion avec Google (django-allauth)
# ---------------------------------------------------------------------------
from urllib.parse import parse_qs, urlparse

from django.test import override_settings

GOOGLE_TEST = {
    'google': {
        'APPS': [{'client_id': 'id-test.apps.googleusercontent.com', 'secret': 'secret-test', 'key': ''}],
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online', 'prompt': 'select_account'},
        'OAUTH_PKCE_ENABLED': True,
    },
}


def connexion_google_simulee(client, email, prenom='Ama', nom='Kossi', uid='1234567890'):
    """Rejoue la fin de la connexion Google (comme au retour de Google) sans appeler Google."""
    from allauth.socialaccount.helpers import complete_social_login
    from allauth.socialaccount.models import SocialAccount, SocialLogin
    from allauth.account.models import EmailAddress
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.contrib.sessions.backends.db import SessionStore
    from django.test import RequestFactory
    from allauth.core import context

    requete = RequestFactory().get('/auth/google/login/callback/')
    requete.session = SessionStore()
    requete.user = __import__('django.contrib.auth.models', fromlist=['AnonymousUser']).AnonymousUser()
    requete._messages = FallbackStorage(requete)
    utilisateur = User(email=email, first_name=prenom, last_name=nom)
    sociallogin = SocialLogin(
        user=utilisateur,
        account=SocialAccount(provider='google', uid=uid, extra_data={'email': email}),
        email_addresses=[EmailAddress(email=email, verified=True, primary=True)],
    )
    with context.request_context(requete):
        reponse = complete_social_login(requete, sociallogin)
    return requete, reponse


@override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE_TEST)
class ConnexionGoogleTests(TestCase):

    def test_bouton_masque_sans_identifiants(self):
        with override_settings(GOOGLE_LOGIN_ACTIVE=False):
            self.assertNotContains(self.client.get(reverse('accounts:connexion')), 'Continuer avec Google')

    def test_bouton_sur_connexion_et_inscription(self):
        with override_settings(GOOGLE_LOGIN_ACTIVE=True):
            for page in ('accounts:connexion', 'accounts:inscription'):
                self.assertContains(self.client.get(reverse(page)), 'Continuer avec Google')

    def test_bouton_envoie_vers_google_avec_pkce(self):
        reponse = self.client.post('/auth/google/login/')
        self.assertEqual(reponse.status_code, 302)
        cible = urlparse(reponse['Location'])
        self.assertEqual(cible.netloc, 'accounts.google.com')
        params = parse_qs(cible.query)
        self.assertEqual(params['client_id'], ['id-test.apps.googleusercontent.com'])
        self.assertIn('code_challenge', params)
        self.assertTrue(params['redirect_uri'][0].endswith('/auth/google/login/callback/'))

    def test_simple_lien_ne_lance_pas_la_connexion(self):
        reponse = self.client.get('/auth/google/login/')
        self.assertNotEqual(urlparse(reponse.get('Location', '')).netloc, 'accounts.google.com')

    def test_pages_allauth_renvoient_vers_celles_du_site(self):
        self.assertRedirects(self.client.get('/auth/login/'), reverse('accounts:connexion'), fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/auth/signup/'), reverse('accounts:inscription'), fetch_redirect_response=False)

    def test_premiere_connexion_cree_le_compte(self):
        requete, reponse = connexion_google_simulee(self.client, 'nouvelle@gmail.com')
        utilisateur = User.objects.get(email='nouvelle@gmail.com')
        self.assertEqual((utilisateur.first_name, utilisateur.last_name), ('Ama', 'Kossi'))
        self.assertTrue(utilisateur.username)
        self.assertFalse(utilisateur.has_usable_password())     # pas de mot de passe : connexion par Google
        self.assertTrue(requete.session.get('proposer_notifications'))
        self.assertEqual(reponse.status_code, 302)
        textes = [str(m) for m in requete._messages]
        self.assertEqual(textes, ['✅ Compte créé avec Google ! Bienvenue chez KcoMat.'])   # un seul message

    def test_email_deja_inscrit_retrouve_le_meme_compte(self):
        existant = User.objects.create_user('kofi', 'kofi@gmail.com', MOT_DE_PASSE)
        connexion_google_simulee(self.client, 'KOFI@gmail.com')
        self.assertEqual(User.objects.filter(email__iexact='kofi@gmail.com').count(), 1)
        self.assertTrue(existant.socialaccount_set.filter(provider='google').exists())

    def test_compte_admin_connecte_mais_admin_garde_le_code(self):
        chef = User.objects.create_superuser('chef', 'chef@gmail.com', MOT_DE_PASSE)
        requete, reponse = connexion_google_simulee(self.client, 'chef@gmail.com')
        self.assertEqual(requete.session.get('_auth_user_id'), str(chef.pk))
        chef.refresh_from_db()
        self.assertTrue(chef.check_password(MOT_DE_PASSE))     # mot de passe conservé pour l'admin
        self.client.force_login(chef)
        reponse = self.client.get('/' + settings.ADMIN_URL.lstrip('/'))
        self.assertEqual(reponse.status_code, 302)
        self.assertIn(settings.ADMIN_2FA_PATH.strip('/'), reponse['Location'])
