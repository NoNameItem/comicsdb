"""comics_db URL Configuration

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
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from comics_db import views, models

router = DefaultRouter(trailing_slash=False)
router.register(r'app_token', views.AppTokenViewSet, basename='app_token')
router.register(r'publisher', views.PublisherViewSet)
router.register(r'universe', views.UniverseViewSet)
router.register(r'title', views.TitleViewSet)
router.register(r'issue', views.IssueViewSet)
router.register(r'parser_run', views.ParserRunViewSet)
router.register(r'cloud_parser_run_details', views.CloudFilesParserRunDetailViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="ComicsDB API Doc",
        default_version='v1',
        description="We are really not trying. What are you waited for?!",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Pages
    path('', TemplateView.as_view(template_name="comics_db/main_page.html"), name="main"),
    path('parser_log', TemplateView.as_view(template_name="comics_db/admin/parser_log.html",
                                            extra_context={'parser_choices': models.ParserRun.PARSER_CHOICES}),
         name="parser_log"),
    path('parser_log/<int:pk>', views.ParserRunDetail.as_view(), name="parser-log-detail"),
    path('run_parser', views.RunParser.as_view(), name="run-parser"),

    # API
    path('api/', include(router.urls)),
    re_path(r'^api/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api-doc', schema_view.with_ui('swagger', cache_timeout=0), name='api-doc'),
    path('api/auth/', include('knox.urls')),
]
