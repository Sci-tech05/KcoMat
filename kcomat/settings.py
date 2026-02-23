"""
Django settings for KcoMat project — Lokossa, Bénin.
"""
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-kcomat-dev-key-changez-en-prod')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

DJANGO_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_tailwind',
    'django_htmx',
]

LOCAL_APPS = [
    'accounts',
    'core',
    'formations',
    'boutique',
    'services',
    'projets',
    'carrieres',
    'partenariats',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/connexion/'
LOGIN_REDIRECT_URL = '/accounts/dashboard/'
LOGOUT_REDIRECT_URL = '/'

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
    # 'site_logo': 'images/logo.png',
    'login_logo': None,
    'login_logo_dark': None,
    # Favicon
    # 'site_icon': 'images/favicon.ico',
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
        {'name': 'Dashboard', 'url': 'admin:index', 'permissions': ['auth.view_user']},
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
        'auth.Group': 'fas fa-users',
        'core.TeamMember': 'fas fa-id-badge',
        'core.Temoignage': 'fas fa-star',
        'core.Statistique': 'fas fa-chart-bar',
        'core.ContactMessage': 'fas fa-envelope',
        'formations.Formation': 'fas fa-graduation-cap',
        'formations.Inscription': 'fas fa-user-plus',
        'formations.Categorie': 'fas fa-folder',
        'boutique.Produit': 'fas fa-microchip',
        'boutique.Categorie': 'fas fa-tags',
        'boutique.Commande': 'fas fa-shopping-cart',
        'boutique.LigneCommande': 'fas fa-list',
        'services.Service': 'fas fa-tools',
        'services.DemandeService': 'fas fa-clipboard-list',
        'projets.Projet': 'fas fa-project-diagram',
        'carrieres.Offre': 'fas fa-briefcase',
        'carrieres.Candidature': 'fas fa-file-alt',
        'partenariats.DemandePartenariat': 'fas fa-handshake',
    },
    # Icône par défaut
    'default_icon_parents': 'fas fa-chevron-circle-right',
    'default_icon_children': 'fas fa-circle',
    # Médias
    'related_modal_active': True,
    'custom_css': None,
    'custom_js': 'js/admin_tabs_hash.js',
    'use_google_fonts_cdn': True,
    # Boutons d\'action en haut
    'show_ui_builder': False,
    'changeform_format': 'horizontal_tabs',
    'changeform_format_overrides': {
        'auth.user': 'vertical_tabs',
        'auth.group': 'vertical_tabs',
    },
    'language_chooser': False,
}

JAZZMIN_UI_TWEAKS = {
    # Thème navbar
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    # Couleur brand (navbar)
    'brand_colour': 'navbar-primary',
    # Accent sidebar
    'accent': 'accent-primary',
    # style navbar: navbar-white | navbar-light | navbar-dark | navbar-primary etc.
    'navbar': 'navbar-white navbar-light',
    # no_navbar_border pour supprimer bordure
    'no_navbar_border': False,
    'navbar_fixed': True,
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
FEDAPAY_SECRET_KEY = config('FEDAPAY_API_KEY', default='')
FEDAPAY_PUBLIC_KEY = config('FEDAPAY_PUBLIC_KEY', default='')
FEDAPAY_SANDBOX = config('FEDAPAY_SANDBOX', default=True, cast=bool)

# Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='kcomat0@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = 'KcoMat <kcomat0@gmail.com>'

# KcoMat Company Info (accessible via context processor)
KCOMAT_INFO = {
    'name': 'KcoMat',
    'slogan': "Maîtrisez les technologies d'aujourd'hui pour construire l'Afrique de demain",
    'phone': '+229 01 96 78 00 99',
    'whatsapp': '22901196780099',
    'email': 'kcomat0@gmail.com',
    'address': 'Lokossa, Département du Mono, Bénin',
    'youtube': 'https://youtube.com/@sympltechofficiel',
    'tiktok': 'https://www.tiktok.com/@kcomat3',
    'facebook': 'https://www.facebook.com/profile.php?id=61581135667007',
    'frais_inscription': 2000,
    'maps_embed': 'https://maps.app.goo.gl/UXMLViYtf7Sjm6267',
}
