"""comicsdb URL Configuration

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
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render_to_response
from django.urls import path, include
from django.contrib.sitemaps import views as sitemap_views
from django.views.decorators.cache import cache_page

from .sitemaps import sitemaps


def robots(request):
    return render_to_response('robots.txt', content_type="text/plain")


urlpatterns = [
                  path('', include("comics_db.urls")),
                  path('robots.txt', robots),
                  path('sitemap.xml', sitemap_views.index, {'sitemaps': sitemaps}),
                  path('sitemap-<section>.xml', sitemap_views.sitemap, {'sitemaps': sitemaps},
                       name='django.contrib.sitemaps.views.sitemap'),
                  path('accounts/', include('registration.backends.default.urls')),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
