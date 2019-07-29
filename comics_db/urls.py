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
from django_celery_beat.models import IntervalSchedule
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
router.register(r'marvel_api_parser_run_details', views.MarvelAPIParserRunDetailViewSet)
router.register(r'marvel_api_creator_merge_details', views.MarvelAPICreatorMergeRunDetailDetailSerializerViewSet)
router.register(r'marvel_api_character_merge_details', views.MarvelAPICharacterMergeRunDetailDetailSerializerViewSet)
router.register(r'marvel_api_event_merge_details', views.MarvelAPIEventMergeRunDetailDetailSerializerViewSet)
router.register(r'marvel_api_title_merge_details', views.MarvelAPITitleMergeRunDetailDetailSerializerViewSet)
router.register(r'marvel_api_issue_merge_details', views.MarvelAPIIssueMergeRunDetailDetailSerializerViewSet)
router.register(r'parser_schedule', views.ParserScheduleViewSet, base_name='parser-schedule')
router.register(r'marvel_api/series', views.MarvelAPISeriesViewSet, base_name='marvel-api-series')

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
    # Main page
    path('', views.MainPageView.as_view(), name="site-main"),

    # Publisher
    path('publishers', views.PublisherListView.as_view(), name="site-publisher-list"),
    path('publisher/<str:slug>', views.PublisherDetailView.as_view(), name="site-publisher-detail"),
    path('publisher/<str:slug>/universes', views.PublisherUniverseListView.as_view(), name="site-publisher-universes"),
    path('publisher/<str:slug>/titles', views.PublisherTitleListView.as_view(), name="site-publisher-titles"),
    path('publisher/<str:slug>/issues', views.PublisherIssueListView.as_view(), name="site-publisher-issues"),

    # Universe
    path('universes', views.UniverseListView.as_view(), name="site-universe-list"),
    path('universe/<str:slug>', views.UniverseDetailView.as_view(), name="site-universe-detail"),
    path('universe/<str:slug>/titles', views.UniverseTitleListView.as_view(), name="site-universe-titles"),
    path('universe/<str:slug>/issues', views.UniverseIssueListView.as_view(), name="site-universe-issues"),

    # Titles
    path('titles', views.TitleListView.as_view(), name="site-title-list"),
    path('title/<str:slug>/', views.TitleDetailView.as_view(), name="site-title-detail"),
    path('title/<str:slug>/issues', views.TitleIssueListView.as_view(), name="site-title-issues"),
    path('title/<str:slug>/delete', views.DeleteTitle.as_view(), name="site-title-delete"),
    path('title/<str:slug>/move-issues', views.MoveTitleIssues.as_view(), name="site-title-move-issues"),
    path('title/<str:slug>/add-to-list', views.AddTitleToReadingList.as_view(), name="site-title-add-to-list"),
    path('title/<str:slug>/download', views.DownloadTitle.as_view(), name="site-title-download"),

    # Issues
    path('issues', views.IssueListView.as_view(), name="site-issue-list"),
    path('issue/<str:slug>/', views.IssueDetailView.as_view(), name="site-issue-detail"),
    path('issue/<str:slug>/mark-read', views.ReadIssue.as_view(), name="site-issue-mark-read"),
    path('issue/<str:slug>/delete', views.DeleteIssue.as_view(), name="site-issue-delete"),
    path('issue/<str:slug>/add-to-list', views.AddToReadingList.as_view(), name="site-issue-add-to-list"),

    # Reading lists
    path('reading-lists', views.ReadingListListView.as_view(), name="site-user-reading-lists"),
    path('reading-list/<str:slug>/', views.ReadingListDetailView.as_view(), name="site-user-reading-list"),
    path('reading-list/<str:slug>/delete', views.DeleteReadingList.as_view(), name="site-reading-list-delete"),
    path('reading-list/<str:slug>/download', views.DownloadReadingList.as_view(), name="site-reading-list-download"),
    path('reading-list/<str:slug>/reorder', views.ChangeReadingOrder.as_view(), name="site-reading-list-reorder"),
    path('reading-list/<str:slug>/delete-issue', views.DeleteFromReadingList.as_view(),
         name="site-reading-list-delete-issue"),
    path('reading-list/<str:list_slug>/issue/<str:slug>', views.ReadingListIssueDetailView.as_view(),
         name="site-reading-list-issue"),

    # Parser log
    path('parser_log', views.ParserLogView.as_view(template_name="comics_db/admin/parser_log.html",
                                                   extra_context={'parser_choices': models.ParserRun.PARSER_CHOICES}),
         name="site-parser-log"),
    path('parser_log/<int:pk>', views.ParserRunDetail.as_view(), name="parser-log-detail"),
    path('run_parser', views.RunParser.as_view(), name="run-parser"),

    # Parser schedule
    path('parser_schedule', TemplateView.as_view(template_name="comics_db/admin/parser_schedule.html",
                                                 extra_context={
                                                     'parser_choices': models.ParserRun.PARSER_CHOICES,
                                                     'period_choices': IntervalSchedule.PERIOD_CHOICES,
                                                 }),

         name="parser-schedule"),

    # Marvel API
    path(r'marvel-api/series/', views.MarvelAPISeriesList.as_view(), name="site-marvel-api-series-list"),
    path(r'marvel-api/series/<int:pk>', views.MarvelAPISeriesDetail.as_view(), name="site-marvel-api-series-detail"),
    path(r'marvel-api/comics/', views.MarvelAPISeriesList.as_view(), name="site-marvel-api-comics-list"),
    path(r'marvel-api/comics/<int:pk>', views.MarvelAPIComicsDetail.as_view(), name="site-marvel-api-comics-detail"),

    # API
    path('api/', include(router.urls)),
    re_path(r'^api/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api-doc', schema_view.with_ui('swagger', cache_timeout=0), name='api-doc'),
    path('api/auth/', include('knox.urls')),
]
