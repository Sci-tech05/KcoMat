"""
URL configuration for kcomat project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.views.generic.base import RedirectView
from django.contrib.sitemaps.views import sitemap
from django.views.decorators.cache import cache_page
from core.admin_security import verify_admin_2fa
from core.sitemaps import SITEMAPS
from core.views import robots_txt
from notifications import views as notifications_views
import sys

admin.site.site_header = "KcoMat Administration"
admin.site.site_title = "KcoMat Admin"
admin.site.index_title = "Tableau de bord KcoMat"

urlpatterns = [
    path(
        'favicon.ico',
        RedirectView.as_view(url=f"{settings.STATIC_URL}img/favicon.svg", permanent=True),
        name='favicon',
    ),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sw.js', notifications_views.service_worker, name='service_worker'),
    path('manifest.webmanifest', notifications_views.manifest, name='manifest'),
    path('sitemap.xml', cache_page(60 * 60)(sitemap), {'sitemaps': SITEMAPS}, name='sitemap'),
    path(settings.ADMIN_2FA_PATH, verify_admin_2fa, name='admin_2fa_verify'),
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('core.urls', namespace='core')),
    path('formations/', include('formations.urls', namespace='formations')),
    path('boutique/', include('boutique.urls', namespace='boutique')),
    path('services/', include('services.urls', namespace='services')),
    path('projets/', include('projets.urls', namespace='projets')),
    path('carrieres/', include('carrieres.urls', namespace='carrieres')),
    path('partenariats/', include('partenariats.urls', namespace='partenariats')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    # Connexion avec Google (django-allauth). Ses pages de compte renvoient vers celles du site.
    path('auth/login/', RedirectView.as_view(pattern_name='accounts:connexion', query_string=True)),
    path('auth/signup/', RedirectView.as_view(pattern_name='accounts:inscription', query_string=True)),
    path('auth/logout/', RedirectView.as_view(pattern_name='accounts:deconnexion')),
    path('auth/password/reset/', RedirectView.as_view(pattern_name='accounts:mdp_oublie')),
    path('auth/', include('allauth.urls')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
elif 'runserver' in sys.argv:
    # En local avec DEBUG=False, runserver ne sert pas MEDIA_URL par defaut.
    media_prefix = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += [
        re_path(
            rf'^{media_prefix}/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        )
    ]
    # En local avec DEBUG=False, servir aussi les statics sans collectstatic.
    static_prefix = settings.STATIC_URL.lstrip('/').rstrip('/')
    urlpatterns += [
        re_path(
            rf'^{static_prefix}/(?P<path>.*)$',
            staticfiles_serve,
            {'insecure': True},
        )
    ]
