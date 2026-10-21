"""
Django settings for KcoMat project — Lokossa, Bénin.
"""
import os
import sys
from pathlib import Path
from decouple import config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_value(name, default=''):
    """Read env var and ignore common placeholder values from .env.example."""
    value = config(name, default=default)
    if isinstance(value, str):
        cleaned = value.strip().strip('"').strip("'")
        if cleaned.lower().startswith('your_') or cleaned.lower() in {'changeme', 'change_me'}:
            return default
        return cleaned
    return value


def required_env(name, *fallback_names):
    """Read a required env var (optionally with legacy fallback names)."""
    value = env_value(name, default='')
    if value:
        return value

    for fallback_name in fallback_names:
        fallback_value = env_value(fallback_name, default='')
        if fallback_value:
            return fallback_value

    raise ImproperlyConfigured(f"Missing required environment variable: {name}")

SECRET_KEY = required_env('SECRET_KEY')


def env_bool(name, default=False):
    raw_value = env_value(name, default=str(default))
    if isinstance(raw_value, bool):
        return raw_value
    value = str(raw_value).strip().lower()
    if value in {'1', 'true', 'yes', 'on', 'y', 'dev', 'debug', 'development'}:
        return True
    if value in {'0', 'false', 'no', 'off', 'n', 'prod', 'production', 'release', ''}:
        return False
    return bool(default)


DEBUG = env_bool('DEBUG', default=False)

def env_list(name, default=''):
    raw_value = env_value(name, default=default)
    if not raw_value:
        return []
    if isinstance(raw_value, str):
        values = raw_value.replace(';', ',').split(',')
    else:
        values = list(raw_value)
    return [str(value).strip() for value in values if str(value).strip()]


DEFAULT_ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'kcomat0.pythonanywhere.com',
]
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', default=','.join(DEFAULT_ALLOWED_HOSTS)) or DEFAULT_ALLOWED_HOSTS
DEFAULT_APP_URL = ''

# Serveur de dev / tests : HTTP local, pas de collectstatic.
IS_LOCAL_COMMAND = any(command in sys.argv for command in ('runserver', 'test'))

# Sécurité
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', default='https://kcomat0.pythonanywhere.com')

# HTTPS : actif par défaut en production, désactivé en local (runserver/test).
# La redirection HTTP -> HTTPS est à activer de préférence via "Force HTTPS"
# dans l'onglet Web de PythonAnywhere (ou SECURE_SSL_REDIRECT=True).
_https_default = not DEBUG and not IS_LOCAL_COMMAND
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', default=False)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', default=_https_default)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', default=_https_default)
SECURE_HSTS_SECONDS = config(
    'SECURE_HSTS_SECONDS',
    default=60 * 60 * 24 * 30 if _https_default else 0,  # 30 jours, à porter à 1 an une fois validé
    cast=int,
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False

DJANGO_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_tailwind',
    'django_htmx',
]

LOCAL_APPS = [
    'accounts',
    'api',
    'core',
    'formations',
    'boutique',
    'services',
    'projets',
    'carrieres',
    'partenariats',
    'notifications',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.admin_security.AdminSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'kcomat.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_context',
                'boutique.context_processors.cart_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'kcomat.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Porto-Novo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Django 5.1 ignore STATICFILES_STORAGE : il faut passer par STORAGES.
# En production, noms hashés + gzip/brotli (WhiteNoise sert alors les fichiers
# avec un cache navigateur d'un an). En local, stockage simple sans collectstatic.
_use_static_manifest = env_bool('STATIC_MANIFEST', default=not DEBUG and not IS_LOCAL_COMMAND)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'core.storage.KcomatStaticFilesStorage'
            if _use_static_manifest
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        ),
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/connexion/'
LOGIN_REDIRECT_URL = '/accounts/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Admin security
_admin_url_raw = env_value('ADMIN_URL', default='admin/')
ADMIN_URL = _admin_url_raw.strip('/').strip()
if not ADMIN_URL:
    ADMIN_URL = 'admin'
ADMIN_URL = f"{ADMIN_URL}/"

_admin_2fa_path_raw = env_value('ADMIN_2FA_PATH', default=f"{ADMIN_URL}verify/")
ADMIN_2FA_PATH = _admin_2fa_path_raw.strip('/').strip()
if not ADMIN_2FA_PATH:
    ADMIN_2FA_PATH = f"{ADMIN_URL}verify".strip('/')
ADMIN_2FA_PATH = f"{ADMIN_2FA_PATH}/"

_admin_allowed_ips_raw = env_value('ADMIN_ALLOWED_IPS', default='127.0.0.1,::1')
ADMIN_ALLOWED_IPS = [ip.strip() for ip in _admin_allowed_ips_raw.split(',') if ip.strip()]
ADMIN_TRUST_X_FORWARDED_FOR = config('ADMIN_TRUST_X_FORWARDED_FOR', default=False, cast=bool)
ADMIN_2FA_CODE_TTL_SECONDS = config('ADMIN_2FA_CODE_TTL_SECONDS', default=300, cast=int)
ADMIN_2FA_MAX_ATTEMPTS = config('ADMIN_2FA_MAX_ATTEMPTS', default=5, cast=int)

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# ============================================================
# JAZZMIN — Admin UI Pro
# ============================================================
JAZZMIN_SETTINGS = {
    # Titre onglet navigateur
    'site_title': 'KcoMat Admin',
    # Titre header navbar admin
    'site_header': 'KcoMat',
    # Texte du lien brand
    'site_brand': 'KcoMat',
    # Logo (chemin relatif depuis /static/)
    'site_logo': 'img/logo.png',
    'site_logo_classes': 'img-rounded',
    'login_logo': None,
    'login_logo_dark': None,
    # Favicon
    'site_icon': 'img/logo.png',
    # Texte accueil
    'welcome_sign': 'Bienvenue sur le panneau d\'administration KcoMat',
    # Liens copyright footer
    'copyright': 'KcoMat — Lokossa, Bénin',
    # Champ de recherche utilisateurs
    'search_model': ['auth.User'],
    # Icîone user top-right
    'user_avatar': None,
    # Lien vers site
    'topmenu_links': [
        {'name': 'Voir le site', 'url': '/', 'new_window': True, 'icon': 'fas fa-globe'},
        {'name': 'Tableau de bord', 'url': 'admin:index', 'permissions': ['auth.view_user']},
        {'model': 'auth.User'},
    ],
    # Sidebar
    'show_sidebar': True,
    'navigation_expanded': True,
    'hide_apps': [],
    'hide_models': [],
    # Ordre apps dans sidebar
    'order_with_respect_to': [
        'auth',
        'accounts',
        'core',
        'formations',
        'boutique',
        'services',
        'projets',
        'carrieres',
        'partenariats',
    ],
    # Icônes personnalisées par app/model
    'icons': {
        'auth': 'fas fa-users-cog',
        'auth.user': 'fas fa-user',
        'auth.group': 'fas fa-users',
        'core': 'fas fa-globe-africa',
        'core.teammember': 'fas fa-id-badge',
        'core.temoignage': 'fas fa-star',
        'core.statistique': 'fas fa-chart-bar',
        'core.contactmessage': 'fas fa-envelope',
        'formations': 'fas fa-graduation-cap',
        'formations.categorieformation': 'fas fa-folder-open',
        'formations.formation': 'fas fa-graduation-cap',
        'formations.inscription': 'fas fa-user-plus',
        'formations.paiementformation': 'fas fa-money-bill-wave',
        'boutique': 'fas fa-store',
        'boutique.categorieproduit': 'fas fa-tags',
        'boutique.produit': 'fas fa-microchip',
        'boutique.commande': 'fas fa-shopping-cart',
        'services': 'fas fa-tools',
        'services.service': 'fas fa-tools',
        'services.demandeservice': 'fas fa-clipboard-list',
        'projets': 'fas fa-project-diagram',
        'projets.categorieprojet': 'fas fa-layer-group',
        'projets.projet': 'fas fa-project-diagram',
        'carrieres': 'fas fa-briefcase',
        'carrieres.offre': 'fas fa-briefcase',
        'carrieres.candidature': 'fas fa-file-alt',
        'partenariats': 'fas fa-handshake',
        'partenariats.partenaire': 'fas fa-building',
        'partenariats.demandepartenariat': 'fas fa-handshake',
        'notifications': 'fas fa-bell',
        'notifications.abonnementpush': 'fas fa-bell',
        'notifications.notificationpush': 'fas fa-paper-plane',
    },
    # Icône par défaut
    'default_icon_parents': 'fas fa-chevron-circle-right',
    'default_icon_children': 'fas fa-circle',
    # Médias
    'related_modal_active': True,
    'custom_css': 'css/admin_premium.css',
    'custom_js': 'js/admin_premium.js',
    'use_google_fonts_cdn': False,  # Inter est chargée par admin_premium.css
    # Boutons d\'action en haut
    'show_ui_builder': False,
    'changeform_format': 'horizontal_tabs',
    # Onglets horizontaux partout : ils défilent sur une ligne (PC et téléphone)
    'changeform_format_overrides': {},
    'language_chooser': False,
}

JAZZMIN_UI_TWEAKS = {
    # Thème navbar
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    # Couleur brand (navbar)
    'brand_colour': False,
    # Accent sidebar
    'accent': 'accent-primary',
    # style navbar: navbar-white | navbar-light | navbar-dark | navbar-primary etc.
    'navbar': 'navbar-white navbar-light',
    # no_navbar_border pour supprimer bordure
    'no_navbar_border': False,
    'navbar_fixed': True,
    # Barre latérale fixe avec son propre défilement (ne bouge plus avec la page)
    'sidebar_fixed': True,
    # Sidebar: sidebar-dark-primary | sidebar-light-primary
    'sidebar': 'sidebar-dark-primary',
    'sidebar_nav_small_text': False,
    'sidebar_disable_expand': False,
    'sidebar_nav_child_indent': True,
    'sidebar_nav_compact_style': False,
    'sidebar_nav_legacy_style': False,
    'sidebar_nav_flat_style': False,
    # darkmode
    'theme': 'default',
    'dark_mode_theme': None,
    # boutons
    'button_classes': {
        'primary': 'btn-primary',
        'secondary': 'btn-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
}

# Fedapay
FEDAPAY_CONFIG = {
    'api_key': required_env('FEDAPAY_API_KEY', 'FEDAPAY_SECRET_KEY'),
    'public_key': required_env('FEDAPAY_PUBLIC_KEY', 'FEDAPAY_PUB_KEY'),
    'environment': required_env('FEDAPAY_ENVIRONMENT'),
    'app_url': env_value('APP_URL', default=DEFAULT_APP_URL),
    'success_url': env_value('FEDAPAY_SUCCESS_URL', default=''),
    'cancel_url': env_value('FEDAPAY_CANCEL_URL', default=''),
}
FEDAPAY_API_TIMEOUT = config('FEDAPAY_API_TIMEOUT', default=60, cast=int)

PAYMENT_CONFIG = {
    'currency': config('PAYMENT_CURRENCY', default='XOF'),
    'country': config('PAYMENT_COUNTRY', default='BJ'),
    'phone_prefix': config('PAYMENT_PHONE_PREFIX', default='+229'),
}

JITSI_BASE_URL = env_value('JITSI_BASE_URL', default='https://framatalk.org')
if isinstance(JITSI_BASE_URL, str):
    JITSI_BASE_URL = JITSI_BASE_URL.strip()
if JITSI_BASE_URL and '://' not in JITSI_BASE_URL:
    JITSI_BASE_URL = f"https://{JITSI_BASE_URL}"
JITSI_BASE_URL = JITSI_BASE_URL.rstrip('/') if JITSI_BASE_URL else ''

# Notifications push (Web Push / VAPID). Clés : python manage.py generer_cles_vapid
VAPID_PUBLIC_KEY = env_value('VAPID_PUBLIC_KEY', default='')
VAPID_PRIVATE_KEY = env_value('VAPID_PRIVATE_KEY', default='')
VAPID_CLAIM_EMAIL = env_value('VAPID_CLAIM_EMAIL', default='kcomat0@gmail.com')
PUSH_ASYNC = env_bool('PUSH_ASYNC', default=True)  # envoi en tâche de fond après publication

FEDAPAY_SECRET_KEY = FEDAPAY_CONFIG['api_key']
FEDAPAY_PUBLIC_KEY = FEDAPAY_CONFIG['public_key']
FEDAPAY_SANDBOX = FEDAPAY_CONFIG['environment'].lower() == 'sandbox'
FEDAPAY_APP_URL = FEDAPAY_CONFIG['app_url'].rstrip('/')
FEDAPAY_SUCCESS_URL = FEDAPAY_CONFIG['success_url']
FEDAPAY_CANCEL_URL = FEDAPAY_CONFIG['cancel_url']

# Email
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='kcomat0@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=20, cast=int)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='KcoMat <kcomat0@gmail.com>')

# KcoMat Company Info (accessible via context processor)
KCOMAT_INFO = {
    'name': 'KcoMat',
    'slogan': "Maîtrisez les technologies d'aujourd'hui pour construire l'Afrique de demain",
    'ifu': '0202290628090',
    'rccm': 'LOKOSSA N° RB/LKS/25 A 10147',
    'phone': '+229 01 96 78 00 99',
    'whatsapp': '22996780099',
    'email': 'kcomat0@gmail.com',
    'address': 'Lokossa, Mono, Bénin',
    'youtube': 'https://youtube.com/@KcoMat',
    'tiktok': 'https://www.tiktok.com/@kcomat3',
    'facebook': 'https://www.facebook.com/profile.php?id=61581135667007',
    'linkedin': 'https://www.linkedin.com/in/kcomat-ets-a7179640a',
    'frais_inscription': 2000,
    'maps_embed': 'https://maps.app.goo.gl/UXMLViYtf7Sjm6267',
}

# Journalisation : erreurs et événements de paiement visibles dans les logs
# PythonAnywhere (stderr) ; les erreurs 500 sont envoyées par e-mail aux ADMINS.
ADMINS = [('KcoMat', KCOMAT_INFO['email'])]
SERVER_EMAIL = DEFAULT_FROM_EMAIL
LOG_LEVEL = config('LOG_LEVEL', default='INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'},
    },
    'formatters': {
        'standard': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'standard'},
        'mail_admins': {
            'class': 'django.utils.log.AdminEmailHandler',
            'level': 'ERROR',
            'filters': ['require_debug_false'],
        },
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'django.request': {'handlers': ['console', 'mail_admins'], 'level': 'ERROR', 'propagate': False},
        'api': {'handlers': ['console', 'mail_admins'], 'level': LOG_LEVEL, 'propagate': False},
        'formations': {'handlers': ['console', 'mail_admins'], 'level': LOG_LEVEL, 'propagate': False},
        'boutique': {'handlers': ['console', 'mail_admins'], 'level': LOG_LEVEL, 'propagate': False},
        'core': {'handlers': ['console', 'mail_admins'], 'level': LOG_LEVEL, 'propagate': False},
        'carrieres': {'handlers': ['console', 'mail_admins'], 'level': LOG_LEVEL, 'propagate': False},
        'notifications': {'handlers': ['console', 'mail_admins'], 'level': LOG_LEVEL, 'propagate': False},
    },
}
