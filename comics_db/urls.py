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
router.register(r'marvel_api_creator_merge_details', views.MarvelAPICreatorMergeRunDetailDetailViewSet)
router.register(r'marvel_api_character_merge_details', views.MarvelAPICharacterMergeRunDetailDetailViewSet)
router.register(r'marvel_api_event_merge_details', views.MarvelAPIEventMergeRunDetailDetailViewSet)
router.register(r'marvel_api_title_merge_details', views.MarvelAPITitleMergeRunDetailDetailViewSet)
router.register(r'marvel_api_issue_merge_details', views.MarvelAPIIssueMergeRunDetailDetailViewSet)
router.register(r'parser_schedule', views.ParserScheduleViewSet, base_name='parser-schedule')
router.register(r'marvel_api/series', views.MarvelAPISeriesViewSet, base_name='marvel-api-series')
router.register(r'marvel_api/comics', views.MarvelAPIComicsViewSet, base_name='marvel-api-comics')

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
    path('publisher/<str:slug>/events', views.PublisherEventListView.as_view(), name="site-publisher-events"),
    path('publisher/<str:slug>/universes', views.PublisherUniverseListView.as_view(), name="site-publisher-universes"),
    path('publisher/<str:slug>/titles', views.PublisherTitleListView.as_view(), name="site-publisher-titles"),
    path('publisher/<str:slug>/issues', views.PublisherIssueListView.as_view(), name="site-publisher-issues"),

    # Creators
    path('creators', views.CreatorListView.as_view(), name="site-creator-list"),
    path('creator/<str:slug>/', views.CreatorDetailView.as_view(), name="site-creator-detail"),
    path('creator/<str:slug>/events', views.CreatorEventListView.as_view(), name="site-creator-events"),
    path('creator/<str:slug>/titles', views.CreatorTitleListView.as_view(), name="site-creator-titles"),
    path('creator/<str:slug>/issues', views.CreatorIssueListView.as_view(), name="site-creator-issues"),

    # Characters
    path('characters', views.CharacterListView.as_view(), name="site-character-list"),
    path('character/<str:slug>/', views.CharacterDetailView.as_view(), name="site-character-detail"),
    path('character/<str:slug>/events', views.CharacterEventListView.as_view(), name="site-character-events"),
    path('character/<str:slug>/titles', views.CharacterTitleListView.as_view(), name="site-character-titles"),
    path('character/<str:slug>/issues', views.CharacterIssueListView.as_view(), name="site-character-issues"),

    # Events
    path('events', views.EventListView.as_view(), name="site-event-list"),
    path('event/<str:slug>/', views.EventDetailView.as_view(), name="site-event-detail"),
    path('event/<str:slug>/titles', views.EventTitleListView.as_view(), name="site-event-titles"),
    path('event/<str:slug>/issues', views.EventIssueListView.as_view(), name="site-event-issues"),

    # Universe
    path('universes', views.UniverseListView.as_view(), name="site-universe-list"),
    path('universe/<str:slug>', views.UniverseDetailView.as_view(), name="site-universe-detail"),
    path('universe/<str:slug>/titles', views.UniverseTitleListView.as_view(), name="site-universe-titles"),
    path('universe/<str:slug>/issues', views.UniverseIssueListView.as_view(), name="site-universe-issues"),

    # Titles
    path('titles', views.TitleListView.as_view(), name="site-title-list"),
    path('title/<str:slug>/', views.TitleDetailView.as_view(), name="site-title-detail"),
    path('title/<str:slug>/issues', views.TitleIssueListView.as_view(), name="site-title-issues"),
    path('title/<str:slug>/delete', views.TitleDelete.as_view(), name="site-title-delete"),
    path('title/<str:slug>/move-issues', views.TitleMoveIssues.as_view(), name="site-title-move-issues"),
    path('title/<str:slug>/add-to-list', views.TitleAddToReadingList.as_view(), name="site-title-add-to-list"),
    path('title/<str:slug>/download', views.TitleDownload.as_view(), name="site-title-download"),

    # Issues
    path('issues', views.IssueListView.as_view(), name="site-issue-list"),
    path('issue/<str:slug>/', views.IssueDetailView.as_view(), name="site-issue-detail"),
    path('issue/<str:slug>/mark-read', views.IssueMarkRead.as_view(), name="site-issue-mark-read"),
    path('issue/<str:slug>/delete', views.IssueDelete.as_view(), name="site-issue-delete"),
    path('issue/<str:slug>/add-to-list', views.IssueAddToReadingList.as_view(), name="site-issue-add-to-list"),

    # Reading lists
    path('reading-lists', views.ReadingListListView.as_view(), name="site-user-reading-lists"),
    path('reading-list/<str:slug>/', views.ReadingListDetailView.as_view(), name="site-user-reading-list"),
    path('reading-list/<str:slug>/delete', views.ReadingListDelete.as_view(), name="site-reading-list-delete"),
    path('reading-list/<str:slug>/download', views.ReadingListDownload.as_view(), name="site-reading-list-download"),
    path('reading-list/<str:slug>/reorder', views.ReadingListChangeOrder.as_view(), name="site-reading-list-reorder"),
    path('reading-list/<str:slug>/delete-issue', views.ReadingListDeleteIssue.as_view(),
         name="site-reading-list-delete-issue"),
    path('reading-list/<str:list_slug>/issue/<str:slug>', views.ReadingListIssueDetailView.as_view(),
         name="site-reading-list-issue"),

    # Parser log
    path('parser_log', views.ParserLogView.as_view(), name="site-parser-log"),
    path('parser_log/<int:pk>', views.ParserRunDetail.as_view(), name="parser-log-detail"),
    path('run_parser', views.ParserRun.as_view(), name="run-parser"),

    # Parser schedule
    path('parser_schedule', views.ParserScheduleView.as_view(), name="parser-schedule"),

    # Marvel API
    path(r'marvel-api/series/', views.MarvelAPISeriesList.as_view(), name="site-marvel-api-series-list"),
    path(r'marvel-api/series/<int:pk>', views.MarvelAPISeriesDetail.as_view(), name="site-marvel-api-series-detail"),
    path(r'marvel-api/comics/', views.MarvelAPIComicsList.as_view(), name="site-marvel-api-comics-list"),
    path(r'marvel-api/comics/<int:pk>', views.MarvelAPIComicsDetail.as_view(), name="site-marvel-api-comics-detail"),

    # API
    path('api/', include(router.urls)),
    re_path(r'^api/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api-doc', schema_view.with_ui('swagger', cache_timeout=0), name='api-doc'),
    path('api/auth/', include('knox.urls')),
]
