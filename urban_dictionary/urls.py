"""urban_dictionary URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from urban_dictionary import settings

urlpatterns = [
    path(r'admin/', admin.site.urls),
    path(r'urban/', include('website.urls', namespace="website")),
    path(r'api/', include('api.urls', namespace="api")),
    path(r'accounts/', include('django_registration.backends.activation.urls')),
    path(r'accounts/', include('django.contrib.auth.urls')),
    path(r'', RedirectView.as_view(url='/urban/', permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'website.views.custom_handler404'
handler500 = 'website.views.custom_handler500'
