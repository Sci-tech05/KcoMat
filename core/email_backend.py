"""Backend SMTP de Django, authentification par AUTH LOGIN quand le serveur la propose.

smtplib choisit AUTH PLAIN par défaut. Gmail (smtp.gmail.com) coupe alors la connexion
(SMTPServerDisconnected) au lieu de répondre, alors qu'en AUTH LOGIN il accepte l'identification
ou renvoie une vraie erreur 535 « Username and Password not accepted ».
"""
import smtplib

from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend


class _AuthLoginMixin:
    def login(self, user, password, *, initial_response_ok=True):
        self.ehlo_or_helo_if_needed()
        if 'LOGIN' in self.esmtp_features.get('auth', '').upper().split():
            self.esmtp_features['auth'] = 'LOGIN'
        return super().login(user, password, initial_response_ok=initial_response_ok)


class _SMTP(_AuthLoginMixin, smtplib.SMTP):
    pass


class _SMTP_SSL(_AuthLoginMixin, smtplib.SMTP_SSL):
    pass


class EmailBackend(DjangoEmailBackend):
    @property
    def connection_class(self):
        return _SMTP_SSL if self.use_ssl else _SMTP
