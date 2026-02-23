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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "KcoMat Administration"
admin.site.site_title = "KcoMat Admin"
admin.site.index_title = "Tableau de bord KcoMat"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls', namespace='core')),
    path('formations/', include('formations.urls', namespace='formations')),
    path('boutique/', include('boutique.urls', namespace='boutique')),
    path('services/', include('services.urls', namespace='services')),
    path('projets/', include('projets.urls', namespace='projets')),
    path('carrieres/', include('carrieres.urls', namespace='carrieres')),
    path('partenariats/', include('partenariats.urls', namespace='partenariats')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

