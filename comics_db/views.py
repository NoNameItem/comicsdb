import datetime
import inspect
import json
import math
import os

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError
from django.db.models import Count, Q, Max, Case, When, F
from django.forms import ModelForm
from django.http import Http404, HttpResponseRedirect, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import formats
from django.views.generic import DetailView, ListView
from django.views.generic.base import View, TemplateView
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from django_filters.rest_framework import DjangoFilterBackend
from drf_multiple_settings.filter_backends.django_filters import FilterBackend
from drf_multiple_settings.viewsets import ReadOnlyModelMultipleSettingsViewSet, MultipleSettingsOrderingFilter
from knox.models import AuthToken
from knox.views import LoginView
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from knox.settings import CONSTANTS, knox_settings
from el_pagination.views import AjaxListView

from comics_db import models, serializers, filtersets, tasks, forms
# from comics_db.models import ReadingListIssue
from comics_db.issue_archive import S3FileWrapper, construct_archive
from comicsdb import settings


########################################################################################################################
# Site
########################################################################################################################


class BreadcrumbMixin:
    breadcrumb = []

    def get_context_data(self, **kwargs):
        context = super(BreadcrumbMixin, self).get_context_data(**kwargs)
        context['breadcrumb'] = self.get_breadcrumb()
        return context

    def get_breadcrumb(self):
        if self.breadcrumb:
            return self.breadcrumb
        else:
            return []


class FormUpdateMixin:
    form_class = None

    def perm_check(self):
        return self.request.user.is_staff

    def success_redirect(self, obj, **kwargs):
        return HttpResponseRedirect(obj.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super(FormUpdateMixin, self).get_context_data(**kwargs)
        context['form'] = self.form_class(instance=self.get_object())
        return context

    def post(self, request, **kwargs):
        if not self.form_class:
            raise RuntimeError("Attribute form_class should be set")
        if not self.perm_check():
            raise PermissionDenied
        obj = self.get_object()
        self.object = self.get_object()
        form = self.form_class(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            obj = form.save()
            return self.success_redirect(obj, **kwargs)
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class SearchMixin:
    search_fields = tuple()

    def search(self, queryset):
        search = self.request.GET.get('search', "")
        if search:
            q = Q()
            for field in self.search_fields:
                q |= Q(**{field: search})
            queryset = queryset.filter(q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(SearchMixin, self).get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', "")
        return context

    def get_queryset(self):
        queryset = super(SearchMixin, self).get_queryset()
        queryset = self.search(queryset)
        return queryset


class SublistMixin:
    parent_model = None
    parent_model_key = "slug"
    parent_model_name_field = "name"
    url_key = "slug"
    parent_field = None

    def get_object(self):
        return get_object_or_404(self.parent_model, **{self.parent_model_key: self.kwargs.get(self.url_key)})

    def get_sublist(self, queryset):
        obj = self.get_object()
        q = queryset.filter(**{self.parent_field: obj})
        return q

    def get_queryset(self):
        queryset = super(SublistMixin, self).get_queryset()
        return self.get_sublist(queryset)

    def get_context_data(self, **kwargs):
        context = super(SublistMixin, self).get_context_data(**kwargs)
        context['sublist_parent'] = getattr(self.get_object(), self.parent_model_name_field, "")
        return context


class CreatorsMixin:
    creators_model = None
    creators_parent_field = None

    ROLE_SORT = {
        "WRITER": 0,
        "PENCILLER": 1,
        "PENCILLER (COVER)": 1,
        "OTHER": 1000,
        "UNKNOWN": 1000
    }

    def get_context_data(self, **kwargs):
        context = super(CreatorsMixin, self).get_context_data(**kwargs)
        creators_queryset = self.creators_model.objects.filter(**{self.creators_parent_field: self.get_object()})
        creators = []
        for query_creator in creators_queryset:
            creator = {
                'slug': query_creator.creator.slug,
                'name': query_creator.creator.name,
                'role': query_creator.role.title().replace("Penciler", "Penciller")
            }
            creator['sort'] = self.ROLE_SORT.get(creator['role'].upper(), 50)
            creators.append(creator)
        creators.sort(key=lambda x: (x['sort'], x['role'], x['name']))
        context['creators'] = creators
        return context


########################################################################################################################
# Main Page
########################################################################################################################


class MainPageView(BreadcrumbMixin, TemplateView):
    template_name = "comics_db/main_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titles_count'] = models.Title.objects.count()
        context['issues_count'] = models.Issue.objects.count()
        context['publishers_count'] = models.Publisher.objects.count()
        context['universes_count'] = models.Universe.objects.count()
        context['characters_count'] = models.Character.objects.count()
        context['creators_count'] = models.Creator.objects.count()
        context['events_count'] = models.Event.objects.count()
        if self.request.user.is_authenticated:
            try:
                context['read'] = models.Issue.objects.filter(readers=self.request.user.profile).count()
                context['total'] = models.Issue.objects.count()
                context['read_total_ratio'] = round(context['read'] / context['total'] * 100)
            except ZeroDivisionError:
                context['read'] = 0
                context['total'] = 0
                context['read_total_ratio'] = 0
        return context


########################################################################################################################
# GLOBAL LISTS AND DETAIL PAGES
########################################################################################################################

########################################################################################################################
# Character
########################################################################################################################


class CharacterListView(BreadcrumbMixin, SearchMixin, AjaxListView):
    template_name = "comics_db/character/list.html"
    context_object_name = "characters"
    page_template = "comics_db/character/list_block.html"
    search_fields = ('name__icontains',)
    queryset = models.Character.objects.filter(
        slug__isnull=False
    ).exclude(
        slug=""
    ).prefetch_related(
        "events", "titles", "issues"
    ).select_related(
        "publisher"
    )
    breadcrumb = [
        {'url': reverse_lazy("site-character-list"), 'text': 'Characters'}
    ]


class CharacterDetailView(BreadcrumbMixin, FormUpdateMixin, DetailView):
    template_name = "comics_db/character/detail.html"
    model = models.Character
    context_object_name = "character"
    extra_context = {'publishers': models.Publisher.objects.all()}
    form_class = forms.CharacterForm

    def get_breadcrumb(self):
        character = self.get_object()
        return [
            {'url': reverse_lazy("site-character-list"), 'text': 'Characters'},
            {'url': reverse_lazy("site-character-detail", args=(character.slug,)), 'text': character.name}
        ]


########################################################################################################################
# Creator
########################################################################################################################


class CreatorListView(BreadcrumbMixin, SearchMixin, AjaxListView):
    template_name = "comics_db/creator/list.html"
    context_object_name = "creators"
    page_template = "comics_db/creator/list_block.html"
    search_fields = ('name__icontains',)
    queryset = models.Creator.objects.filter(
        slug__isnull=False
    ).exclude(
        slug=""
    ).prefetch_related(
        "issues", "titles", "events"
    )
    breadcrumb = [
        {'url': reverse_lazy("site-creator-list"), 'text': 'Creators'}
    ]


class CreatorDetailView(BreadcrumbMixin, FormUpdateMixin, DetailView):
    template_name = "comics_db/creator/detail.html"
    model = models.Creator
    context_object_name = "creator"
    form_class = forms.CreatorForm

    def get_breadcrumb(self):
        creator = self.get_object()
        return [
            {'url': reverse_lazy("site-creator-list"), 'text': 'Creators'},
            {'url': reverse_lazy("site-creator-detail", args=(creator.slug,)), 'text': creator.name}
        ]


########################################################################################################################
# Event
########################################################################################################################


class EventListView(BreadcrumbMixin, SearchMixin, AjaxListView):
    template_name = "comics_db/event/list.html"
    context_object_name = "events"
    page_template = "comics_db/event/list_block.html"
    search_fields = ('name__icontains',)
    queryset = models.Event.objects.select_related(
        "publisher"
    ).prefetch_related(
        "issues", "titles"
    )
    breadcrumb = [
        {'url': reverse_lazy("site-event-list"), 'text': 'Events'}
    ]


class EventDetailView(BreadcrumbMixin, FormUpdateMixin, CreatorsMixin, DetailView):
    template_name = "comics_db/event/detail.html"
    model = models.Event
    context_object_name = "event"
    form_class = forms.EventForm
    extra_context = {'publishers': models.Publisher.objects.all()}
    creators_model = models.EventCreator
    creators_parent_field = "event"

    def get_breadcrumb(self):
        event = self.get_object()
        return [
            {'url': reverse_lazy("site-event-list"), 'text': 'Events'},
            {'url': reverse_lazy("site-event-detail", args=(event.slug,)), 'text': event.name}
        ]


########################################################################################################################
# Issue
########################################################################################################################


class IssueListView(BreadcrumbMixin, SearchMixin, AjaxListView):
    template_name = "comics_db/issue/list.html"
    context_object_name = "issues"
    page_template = "comics_db/issue/list_block.html"
    search_fields = ('name__icontains', 'title__name__icontains', 'title__title_type__name__icontains',
                     'title__publisher__name__icontains', 'title__universe__name__icontains')
    queryset = models.Issue.objects.all().select_related("title__publisher", "title__universe",
                                                         "title__title_type")
    breadcrumb = [
        {'url': reverse_lazy("site-issue-list"), 'text': 'Issues'}
    ]

    def get_queryset(self):
        queryset = super(IssueListView, self).get_queryset()
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(read=Count('readers', distinct=True,
                                                    filter=Q(readers=self.request.user.profile)))
        try:
            hide_read = self.request.GET.get('hide-read')
            if hide_read == 'on':
                queryset = queryset.exclude(read=1)
            return queryset
        except KeyError:
            return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_read'] = self.request.GET.get('hide-read')
        return context


class IssueDetailView(BreadcrumbMixin, FormUpdateMixin, CreatorsMixin, DetailView):
    template_name = "comics_db/issue/detail.html"
    model = models.Issue
    context_object_name = "issue"
    form_class = forms.IssueForm
    creators_model = models.IssueCreator
    creators_parent_field = "issue"

    def get_breadcrumb(self):
        issue = self.get_object()
        return [
            {'url': reverse_lazy("site-issue-list"), 'text': 'Issues'},
            {'url': reverse_lazy("site-issue-detail", args=(issue.slug,)), 'text': issue.name}
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_link'] = self.request.META.get('HTTP_REFERER', reverse('site-issue-list'))
        if self.request.user.is_authenticated:
            context['reading_lists'] = self.request.user.profile.reading_lists.order_by('name')
        try:
            issue = self.object
            r = models.ReadIssue.objects.get(issue=issue, profile=self.request.user.profile)
            read_date = r.read_date
        except (models.ReadIssue.DoesNotExist, AttributeError):
            read_date = None
        context['read_date'] = read_date
        return context


class IssueDelete(View, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, slug):
        redirect_url = request.POST.get('delete-redirect-url')
        issue = models.Issue.objects.get(slug=slug)
        issue.delete()
        return HttpResponseRedirect(redirect_url)


class IssueMarkRead(View, LoginRequiredMixin):
    def post(self, request, slug):
        try:
            issue = models.Issue.objects.get(slug=slug)
            profile = request.user.profile
            issue.readers.add(profile)
            # r = models.ReadIssue(profile=profile, issue=issue)
            # r.save()
            return JsonResponse({'status': "success", 'issue_name': issue.name,
                                 'date': formats.localize(datetime.date.today(), use_l10n=True)
                                 })
        except IntegrityError:
            return JsonResponse({'status': 'error', 'message': 'You already marked this issue as read'})
        except Exception as err:
            return JsonResponse({'status': 'error', 'message': 'Unknown error, please contact administrator. \n'
                                                               'Error message: %s' % err.args[0]})


class IssueAddToReadingList(View, LoginRequiredMixin):
    def post(self, request, slug):
        try:
            issue = models.Issue.objects.get(slug=slug)
            reading_list = self.request.user.profile.reading_lists.get(pk=request.POST.get('list_id'))
            order = models.ReadingListIssue.objects.filter(reading_list=reading_list).aggregate(max_order=Max('order'))[
                        'max_order'] \
                    or 0
            reading_list.issues.add(issue, through_defaults={'order': order + 1})
            reading_list.save()
            return JsonResponse({'status': "success", 'issue_name': issue.name,
                                 'list_name': reading_list.name})
        except models.Issue.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Issue not found."})
        except models.ReadingList.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Reading list not found. Please refresh page."})
        except Exception as err:
            return JsonResponse({'status': 'error', 'message': 'Unknown error, please contact administrator. \n'
                                                               'Error message: %s' % err.args[0]})


########################################################################################################################
# Marvel API Comics
########################################################################################################################


class MarvelAPIComicsList(BreadcrumbMixin, UserPassesTestMixin, TemplateView):
    template_name = "comics_db/admin/marvel_api_comics_list.html"
    breadcrumb = [
        {'url': "", 'text': 'Marvel API'},
        {'url': reverse_lazy("site-marvel-api-comics-list"), 'text': 'Comics'},
    ]

    def test_func(self):
        return self.request.user.is_staff


class MarvelAPIComicsDetail(BreadcrumbMixin, UserPassesTestMixin, DetailView):
    model = models.MarvelAPIComics
    context_object_name = 'api_comic'
    template_name = "comics_db/admin/marvel_api_comics_detail.html"

    def get_breadcrumb(self):
        comic = self.get_object()
        return [
            {'url': "", 'text': 'Marvel API'},
            {'url': reverse_lazy("site-marvel-api-comics-list"), 'text': 'Comics'},
            {'url': reverse_lazy("site-marvel-api-comics-detail", args=(comic.id,)), 'text': comic.title},
        ]

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super(MarvelAPIComicsDetail, self).get_context_data(**kwargs)
        api_comic = context['api_comic']
        try:
            api_image = api_comic.image
            link = "{0.path}.{0.extension}".format(api_image)
            context['image_link'] = link
        except models.MarvelAPIImage.DoesNotExist:
            context['image_link'] = None
        try:
            context['publish_date'] = api_comic.dates.get(type="onsaleDate").date
        except models.MarvelAPISiteUrl.DoesNotExist:
            pass
        return context


########################################################################################################################
# Marvel API Series
########################################################################################################################


class MarvelAPISeriesList(BreadcrumbMixin, UserPassesTestMixin, TemplateView):
    template_name = "comics_db/admin/marvel_api_series_list.html"
    breadcrumb = [
        {'url': "", 'text': 'Marvel API'},
        {'url': reverse_lazy("site-marvel-api-series-list"), 'text': 'Series'},
    ]
    extra_context = {'TYPE_CHOICES': filtersets.MARVEL_API_SERIES_TYPE_CHOICES}

    def test_func(self):
        return self.request.user.is_staff


class MarvelAPISeriesDetail(BreadcrumbMixin, UserPassesTestMixin, DetailView):
    model = models.MarvelAPISeries
    context_object_name = 'api_series'
    template_name = "comics_db/admin/marvel_api_series_detail.html"

    def get_breadcrumb(self):
        series = self.get_object()
        return [
            {'url': "", 'text': 'Marvel API'},
            {'url': reverse_lazy("site-marvel-api-series-list"), 'text': 'Series'},
            {'url': reverse_lazy("site-marvel-api-series-detail", args=(series.id,)), 'text': series.title},
        ]

    def test_func(self):
        return self.request.user.is_staff


########################################################################################################################
# Parser log
########################################################################################################################


class ParserLogView(BreadcrumbMixin, UserPassesTestMixin, TemplateView):
    template_name = "comics_db/admin/parser_log.html"
    extra_context = {'parser_choices': models.ParserRun.PARSER_CHOICES}
    breadcrumb = [
        {'url': reverse_lazy("site-parser-log"), 'text': 'Parsers log'}
    ]

    def test_func(self):
        return self.request.user.is_staff


class ParserRunDetail(BreadcrumbMixin, UserPassesTestMixin, DetailView):
    model = models.ParserRun
    context_object_name = 'parser_run'
    template_name = "comics_db/admin/parser_run.html"
    breadcrumb = [
        {'url': reverse_lazy("site-parser-log"), 'text': 'Parsers log'},
        {'url': "", 'text': 'Parser run details'},
    ]

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status_css = None
        if self.object.status in ("RUNNING", "COLLECTING"):
            status_css = 'info'
        elif self.object.status == "SUCCESS":
            status_css = 'success'
        elif self.object.status == "ENDED_WITH_ERRORS":
            status_css = 'warning'
        elif self.object.status in ("CRITICAL_ERROR", "INVALID_PARSER"):
            status_css = 'danger'
        context['status_css'] = status_css
        return context


class ParserRun(UserPassesTestMixin, View):
    parser_dict = dict(models.ParserRun.PARSER_CHOICES)

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request):
        try:
            parser = request.POST['parser_code']
            args = tuple()
            parser_name = self.parser_dict.get(parser)
            if not parser or parser == 'BASE':
                return JsonResponse({'status': 'error', 'message': 'Invalid parser code "%s"' % parser})
            if parser == 'CLOUD_FILES':
                path_root = request.POST['cloud-path-root']
                if not path_root:
                    return JsonResponse({'status': 'error', 'message': 'Path root should be specified'})
                full = bool(request.POST['cloud-full'])
                load_covers = bool(request.POST['cloud-load-cover'])
                marvel_api_merge = bool(request.POST['cloud-marvel-api-merge'])
                args = (path_root, full, load_covers, marvel_api_merge)
            elif parser == 'MARVEL_API':
                incremental = request.POST['marvel-api-incremental']
                args = (incremental,)
            elif parser == "FULL_MARVEL_API_MERGE":
                parser_name = "Full Marvel API Merge"
            tasks.parser_run_task.delay(parser, args)
            return JsonResponse({'status': 'success', 'message': '%s started' % parser_name})
        except Exception as err:
            return JsonResponse({'status': 'error', 'message': err.args[0]})


########################################################################################################################
# Parser Schedule
########################################################################################################################


class ParserScheduleView(BreadcrumbMixin, UserPassesTestMixin, TemplateView):
    template_name = "comics_db/admin/parser_schedule.html"
    extra_context = {
        'parser_choices': models.ParserRun.PARSER_CHOICES,
        'period_choices': IntervalSchedule.PERIOD_CHOICES,
    }
    breadcrumb = [
        {'url': reverse_lazy("parser-schedule"), 'text': 'Parsers schedule'}
    ]

    def test_func(self):
        return self.request.user.is_staff


########################################################################################################################
# Publisher
########################################################################################################################


class PublisherListView(BreadcrumbMixin, SearchMixin, ListView):
    template_name = "comics_db/publisher/list.html"
    context_object_name = "publishers"
    search_fields = ('name__icontains',)
    queryset = models.Publisher.objects.all()
    breadcrumb = [
        {'url': reverse_lazy("site-publisher-list"), 'text': 'Publishers'}
    ]


class PublisherDetailView(BreadcrumbMixin, FormUpdateMixin, DetailView):
    template_name = "comics_db/publisher/detail.html"
    model = models.Publisher
    context_object_name = "publisher"
    form_class = forms.PublisherForm

    def get_breadcrumb(self):
        publisher = self.get_object()
        return [
            {'url': reverse_lazy("site-publisher-list"), 'text': 'Publishers'},
            {'url': reverse_lazy("site-publisher-detail", args=(publisher.slug,)), 'text': publisher.name}
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            try:
                context['read'] = models.Issue.objects.filter(readers=self.request.user.profile,
                                                              title__publisher=self.get_object()).count()
                context['total'] = models.Issue.objects.filter(title__publisher=self.get_object()).count()
                context['read_total_ratio'] = round(context['read'] / context['total'] * 100)
            except ZeroDivisionError:
                context['read'] = 0
                context['total'] = 0
                context['read_total_ratio'] = 0
        return context


########################################################################################################################
# Reading lists
########################################################################################################################


class ReadingListListView(BreadcrumbMixin, ListView, LoginRequiredMixin):
    template_name = "comics_db/profile/list.html"
    context_object_name = "reading_lists"
    breadcrumb = [
        {'url': reverse_lazy("site-user-reading-lists"), 'text': 'My reading lists'}
    ]

    def get_queryset(self):
        return self.request.user.profile.reading_lists.all().annotate(total=Count('issues', distinct=True)) \
            .annotate(read=Count('issues', distinct=True, filter=Q(issues__readers=self.request.user.profile))) \
            .annotate(read_total_ratio=Case(When(total=0, then=0),
                                            default=F('read') * 100 / F('total')))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sorting_choices'] = models.ReadingList.SORTING_CHOICES
        return context

    def post(self, request):
        form = forms.ReadingListForm(request.POST)
        self.object_list = self.get_queryset()
        context = self.get_context_data(object_list=self.object_list)
        if form.is_valid():
            form.save()
        else:
            context['form'] = form
        return self.render_to_response(context)


class ReadingListDetailView(BreadcrumbMixin, FormUpdateMixin, AjaxListView):
    template_name = "comics_db/profile/issue_list.html"
    context_object_name = "issues"
    page_template = "comics_db/profile/issue_list_block.html"
    search_fields = (
        'issue__name__icontains', 'issue__title__name__icontains', 'issue__title__title_type__name__icontains',
        'issue__title__publisher__name__icontains', 'issue__title__universe__name__icontains')
    form_class = forms.ReadingListForm

    def get_breadcrumb(self):
        breadcrumb = []
        if self.request.user.is_authenticated and self.reading_list.owner == self.request.user.profile:
            breadcrumb.append({'url': reverse_lazy("site-user-reading-lists"), 'text': 'My reading lists'})
        else:
            breadcrumb.append({'url': '', 'text': 'Reading lists'})
        breadcrumb.append({'url': reverse_lazy("site-user-reading-list", args=(self.reading_list.slug,)),
                           'text': self.reading_list.name})
        return breadcrumb

    def get_queryset(self):
        # Get all reading list
        self.reading_list = models.ReadingList.objects.all()

        # Join read stats
        if self.request.user.is_authenticated:
            self.reading_list = self.reading_list.annotate(total=Count('issues', distinct=True)) \
                .annotate(read=Count('issues', distinct=True, filter=Q(issues__readers=self.request.user.profile))) \
                .annotate(read_total_ratio=Case(When(total=0, then=0),
                                                default=F('read') * 100 / F('total')))

        # Get current reading list
        self.reading_list = self.reading_list.get(slug=self.kwargs['slug'])

        # Get all issues in reading list and join publisher, universe and title
        # queryset = self.reading_list.issues.select_related("title__publisher", "title__universe",
        #                                                    "title__title_type")

        queryset = models.ReadingListIssue.objects.filter(
            reading_list=self.reading_list).select_related(
            "issue",
            "issue__title",
            "issue__title__publisher",
            "issue__title__universe",
            "issue__title__title_type")

        # Get read status if user is authenticated
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(read=Count('issue__readers', distinct=True,
                                                    filter=Q(issue__readers=self.request.user.profile)))

        # Filter and hide read
        try:
            search = self.request.GET.get('search', None)
            hide_read = self.request.GET.get('hide-read')
            if hide_read == 'on':
                queryset = queryset.exclude(read=1)
            if search:
                q = Q()
                for field in self.search_fields:
                    q |= Q(**{field: search})
                queryset = queryset.filter(q)
            queryset = queryset
        except KeyError:
            queryset = queryset

        # Ordering
        if self.reading_list.sorting == 'MANUAL':
            queryset = queryset.order_by('order')
        else:
            queryset = queryset.order_by('issue__title', 'issue__number')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', "")
        context['hide_read'] = self.request.GET.get('hide-read')
        context['reading_list'] = self.reading_list
        context['edit'] = self.request.user.is_authenticated and self.reading_list.owner == self.request.user.profile
        context['sorting_choices'] = models.ReadingList.SORTING_CHOICES
        return context

    def perm_check(self):
        rl = get_object_or_404(models.ReadingList, slug=self.kwargs.get('slug'))
        return self.request.user.is_authenticated and rl.owner == self.request.user.profile

    def get_object(self):
        return get_object_or_404(models.ReadingList, slug=self.kwargs.get('slug'))


class ReadingListDelete(View, LoginRequiredMixin):
    def post(self, request, slug):
        if not request.user.is_authenticated:
            raise PermissionError
        reading_list = self.request.user.profile.reading_lists.get(slug=slug)
        reading_list.delete()
        return JsonResponse({'status': 'success'})


class ReadingListChangeOrder(View, LoginRequiredMixin):
    def post(self, request, slug):
        if not request.user.is_authenticated:
            raise PermissionError
        try:
            reading_list = self.request.user.profile.reading_lists.get(slug=slug)
            old_pos = int(self.request.POST['oldPos'])
            new_pos = int(self.request.POST['newPos'])
            issue_id = int(self.request.POST['issueID'])

            if old_pos < new_pos:
                models.ReadingListIssue.objects.filter(reading_list=reading_list, order__gt=old_pos, order__lte=new_pos) \
                    .update(order=F('order') - 1)
            else:
                models.ReadingListIssue.objects.filter(reading_list=reading_list, order__gte=new_pos, order__lt=old_pos) \
                    .update(order=F('order') + 1)

            rl_issue = models.ReadingListIssue.objects.get(reading_list=reading_list, issue_id=issue_id)
            rl_issue.order = new_pos
            rl_issue.save()

            return JsonResponse({'status': 'success'})
        except KeyError:
            return JsonResponse({'status': "error", 'message': "Can't get new order."})


class ReadingListDeleteIssue(View, LoginRequiredMixin):
    def post(self, request, slug):
        try:
            reading_list = request.user.profile.reading_lists.get(slug=slug)
            issue = reading_list.issues.get(pk=request.POST.get('issue_id'))
            rl_issue = models.ReadingListIssue.objects.get(reading_list=reading_list, issue=issue)
            order = rl_issue.order
            models.ReadingListIssue.objects.filter(reading_list=reading_list, order__gt=order).update(
                order=F("order") - 1)
            reading_list.issues.remove(issue)
            reading_list.save()
            reading_list = request.user.profile.reading_lists.annotate(
                total=Count('issues', distinct=True)) \
                .annotate(read=Count('issues', distinct=True, filter=Q(issues__readers=self.request.user.profile))) \
                .annotate(read_total_ratio=Case(When(total=0, then=0),
                                                default=F('read') * 100 / F('total'))).get(slug=slug)
            return JsonResponse({'status': "success", 'issue_name': issue.name, 'list_name': reading_list.name,
                                 'read': reading_list.read, 'total': reading_list.total,
                                 'read_total_ratio': reading_list.read_total_ratio})
        except models.ReadingList.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Reading list not found."})
        except models.Issue.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Issue not found. Please refresh page"})
        except Exception as err:
            return JsonResponse({'status': 'error', 'message': 'Unknown error, please contact administrator. \n'
                                                               'Error message: %s' % err.args[0]})


class ReadingListIssueDetailView(BreadcrumbMixin, FormUpdateMixin, DetailView):
    template_name = "comics_db/profile/reading_list_issue.html"
    context_object_name = "issue"
    form_class = forms.IssueForm

    def get_breadcrumb(self):
        breadcrumb = []
        if self.request.user.is_authenticated and self.reading_list.owner == self.request.user.profile:
            breadcrumb.append({'url': reverse_lazy("site-user-reading-lists"), 'text': 'My reading lists'})
        else:
            breadcrumb.append({'url': '', 'text': 'Reading lists'})
        breadcrumb.append({'url': reverse_lazy("site-user-reading-list", args=(self.reading_list.slug,)),
                           'text': self.reading_list.name})
        breadcrumb.append({'url': reverse_lazy("site-reading-list-issue", args=(self.reading_list.slug, self.object.slug)),
                           'text': self.object.name})
        return breadcrumb

    def get_queryset(self):
        self.reading_list = models.ReadingList.objects.all()

        if self.request.user.is_authenticated:
            self.reading_list = self.reading_list.annotate(total=Count('issues', distinct=True)) \
                .annotate(read=Count('issues', distinct=True, filter=Q(issues__readers=self.request.user.profile))) \
                .annotate(read_total_ratio=Case(When(total=0, then=0),
                                                default=F('read') * 100 / F('total')))

        self.reading_list = self.reading_list.get(slug=self.kwargs['list_slug'])

        queryset = self.reading_list.issues.all()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_link'] = self.request.META.get('HTTP_REFERER', reverse('site-issue-list'))
        if self.request.user.is_authenticated:
            context['reading_lists'] = self.request.user.profile.reading_lists.order_by('name')
        issue = self.object
        try:
            r = models.ReadIssue.objects.get(issue=issue, profile=self.request.user.profile)
            read_date = r.read_date
        except (models.ReadIssue.DoesNotExist, AttributeError):
            read_date = None
        context['read_date'] = read_date
        context['reading_list'] = self.reading_list
        context['edit'] = self.request.user.is_authenticated and self.reading_list.owner == self.request.user.profile

        if self.reading_list.sorting == "MANUAL":
            rl_issue = models.ReadingListIssue.objects.get(reading_list=self.reading_list, issue=issue)
            try:
                context['previous_issue'] = models.ReadingListIssue.objects.get(reading_list=self.reading_list,
                                                                                order=rl_issue.order - 1).issue
            except models.ReadingListIssue.DoesNotExist:
                context['previous_issue'] = None

            try:
                context['next_issue'] = models.ReadingListIssue.objects.get(reading_list=self.reading_list,
                                                                            order=rl_issue.order + 1).issue
            except models.ReadingListIssue.DoesNotExist:
                context['next_issue'] = None

        else:
            issues = list(self.reading_list.issues.all())
            current_number = issues.index(issue)
            if current_number > 0:
                context['previous_issue'] = issues[current_number - 1]
            if current_number < len(issues) - 1:
                context['next_issue'] = issues[current_number + 1]

        return context

    def success_redirect(self, obj, **kwargs):
        return HttpResponseRedirect(reverse('site-reading-list-issue', args=(kwargs['list_slug'], kwargs['slug'])))


class ReadingListDownload(View):
    def get(self, request, slug):
        rl = get_object_or_404(models.ReadingList, slug=slug)

        queryset = models.ReadingListIssue.objects.filter(reading_list=rl).select_related('issue', 'issue__title')

        if rl.sorting == 'MANUAL':
            queryset = queryset.order_by('order')
            num_length = math.ceil(math.log10(queryset.count()))

            issues = [
                (
                    "{list_name}/{num} - [{issue.title.name}]{issue.name}.{issue_ext}".format(
                        list_name=rl,
                        num=str(num).rjust(num_length, '0'),
                        issue=rl_issue.issue,
                        issue_ext=os.path.splitext(rl_issue.issue.link)[1]
                    ),
                    rl_issue.issue.link
                )
                for num, rl_issue in enumerate(queryset, 1)
            ]

        else:
            issues = [
                (
                    "{list_name}/{title}/[{title.name}]{issue_name}.{issue_ext}".format(
                        list_name=rl,
                        title=rl_issue.issue.title,
                        issue_name=rl_issue.issue.name,
                        issue_ext=os.path.splitext(rl_issue.issue.link)[1]
                    ),
                    rl_issue.issue.link
                )
                for num, rl_issue in enumerate(queryset)
            ]

        z = construct_archive(issues)

        response = StreamingHttpResponse(z, content_type="application/zip")
        response['Content-Disposition'] = "attachment; filename=\"{0}.zip\"".format(rl)
        return response


########################################################################################################################
# Title
########################################################################################################################


class TitleListView(BreadcrumbMixin, SearchMixin, AjaxListView):
    template_name = "comics_db/title/list.html"
    context_object_name = "titles"
    page_template = "comics_db/title/list_block.html"
    search_fields = ('name__icontains', 'title_type__name__icontains', 'publisher__name__icontains',
                     'universe__name__icontains')
    queryset = models.Title.objects.annotate(issue_count=Count('issues')).select_related("publisher", "universe",
                                                                                         "title_type")
    breadcrumb = [
        {'url': reverse_lazy("site-title-list"), 'text': 'Titles'}
    ]

    def get_queryset(self):
        queryset = super(TitleListView, self).get_queryset()
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                read_issue_count=Count('issues', filter=Q(issues__readers=self.request.user.profile)))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title_types'] = models.TitleType.objects.all()
        context['publishers'] = models.Publisher.objects.all()
        context['universes'] = models.Universe.objects.all()
        return context

    def post(self, request):
        if not self.request.user.is_staff:
            raise PermissionDenied
        self.object_list = self.get_queryset()
        context = self.get_context_data(object_list=self.object_list, page_template=self.page_template)
        form = forms.TitleCreateForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.save()
        else:
            context['form'] = form
        return self.render_to_response(context)


class TitleDetailView(BreadcrumbMixin, FormUpdateMixin, CreatorsMixin, DetailView):
    template_name = "comics_db/title/detail.html"
    model = models.Title
    context_object_name = "title"
    form_class = forms.TitleForm
    creators_parent_field = "title"
    creators_model = models.TitleCreator

    def get_breadcrumb(self):
        title = self.get_object()
        return [
            {'url': reverse_lazy("site-title-list"), 'text': 'Titles'},
            {'url': reverse_lazy("site-title-detail", args=(title.slug,)), 'text': title.name}
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title_types'] = models.TitleType.objects.all()
        context['list_link'] = self.request.META.get('HTTP_REFERER', reverse('site-title-list'))
        if self.request.user.is_authenticated:
            context['reading_lists'] = self.request.user.profile.reading_lists.order_by('name')
            try:
                context['read'] = models.Issue.objects.filter(readers=self.request.user.profile,
                                                              title=self.object).count()
                context['total'] = models.Issue.objects.filter(title=self.object).count()
                context['read_total_ratio'] = round(context['read'] / context['total'] * 100)
                if context['read'] == context['total']:
                    issues = self.object.issues.all()
                    context['read_date'] = models.ReadIssue.objects.filter(issue__in=issues,
                                                                           profile=self.request.user.profile) \
                        .aggregate(Max('read_date'))['read_date__max']
            except ZeroDivisionError:
                context['read'] = 0
                context['total'] = 0
                context['read_total_ratio'] = 0
                context['read_date'] = None
        return context


class TitleDelete(View, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, slug):
        redirect_url = request.POST.get('delete-redirect-url')
        title = models.Title.objects.get(slug=slug)
        title.delete()
        return HttpResponseRedirect(redirect_url)


class TitleMoveIssues(View, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, slug):
        target_title_id = request.POST.get('target-title-id')
        target_title = get_object_or_404(models.Title, id=target_title_id)
        source_title = get_object_or_404(models.Title, slug=slug)
        source_title.issues.update(title=target_title)
        if target_title != source_title:
            source_title.delete()
        return HttpResponseRedirect(target_title.site_link)


class TitleAddToReadingList(View, LoginRequiredMixin):
    def post(self, request, slug):
        try:
            title = models.Title.objects.get(slug=slug)
            reading_list = self.request.user.profile.reading_lists.get(pk=request.POST.get('list_id'))
            added_issues = list(reading_list.issues.filter(title=title))
            issues = title.issues.all()
            number_from = request.POST.get('number_from')
            number_to = request.POST.get('number_to')
            if number_from:
                issues = issues.filter(number__gte=number_from)
            if number_to:
                issues = issues.filter(number__lte=number_to)
            issues.order_by('number')
            order = models.ReadingListIssue.objects.filter(reading_list=reading_list).aggregate(max_order=Max('order'))[
                        'max_order'] or 0
            rl_issues = []
            for issue in issues:
                order += 1

                if issue not in added_issues:
                    rl_issue = models.ReadingListIssue(reading_list=reading_list, issue=issue, order=order)
                    rl_issues.append(rl_issue)

            models.ReadingListIssue.objects.bulk_create(rl_issues)
            return JsonResponse({'status': "success", 'issue_count': len(rl_issues),
                                 'list_name': reading_list.name})
        except models.Title.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Title not found."})
        except models.ReadingList.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Reading list not found. Please refresh page."})
        except Exception as err:
            return JsonResponse({'status': 'error', 'message': 'Unknown error, please contact administrator. \n'
                                                               'Error message: %s' % err.args[0]})


class TitleDownload(View):
    def get(self, request, slug):
        title = get_object_or_404(models.Title, slug=slug)

        issues = list(
            map(lambda x: ("{0}/[{0.name}] {1}.{2}".format(title, x.name, os.path.splitext(x.link)[1]), x.link),
                title.issues.all()))

        z = construct_archive(issues)

        response = StreamingHttpResponse(z, content_type="application/zip")
        response['Content-Disposition'] = "attachment; filename=\"{0}.zip\"".format(title)

        return response


########################################################################################################################
# Universe
########################################################################################################################


class UniverseListView(BreadcrumbMixin, SearchMixin, ListView):
    template_name = "comics_db/universe/list.html"
    queryset = models.Universe.objects.all()
    context_object_name = "universes"
    search_fields = ('name__icontains', "publisher__name__icontains")
    breadcrumb = [
        {'url': reverse_lazy("site-universe-list"), 'text': 'Universes'}
    ]


class UniverseDetailView(BreadcrumbMixin, FormUpdateMixin, DetailView):
    template_name = "comics_db/universe/detail.html"
    model = models.Universe
    context_object_name = "universe"
    form_class = forms.UniverseForm

    def get_breadcrumb(self):
        universe = self.get_object()
        return [
            {'url': reverse_lazy("site-universe-list"), 'text': 'Universes'},
            {'url': reverse_lazy("site-universe-detail", args=(universe.slug,)), 'text': universe.name}
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            try:
                context['read'] = models.Issue.objects.filter(readers=self.request.user.profile,
                                                              title__universe=self.get_object()).count()
                context['total'] = models.Issue.objects.filter(title__universe=self.get_object()).count()
                context['read_total_ratio'] = round(context['read'] / context['total'] * 100)
            except ZeroDivisionError:
                context['read'] = 0
                context['total'] = 0
                context['read_total_ratio'] = 0
        return context

    # def post(self, request, slug):
    #     if not self.request.user.is_staff:
    #         raise PermissionDenied
    #     self.object = self.get_object()
    #     form = forms.UniverseForm(request.POST, request.FILES)
    #     if form.is_valid():
    #         self.object.poster = form.cleaned_data['poster'] or self.object.poster
    #         self.object.desc = form.cleaned_data['desc']
    #         self.object.save()
    #     context = self.get_context_data(object=self.object, form=form)
    #     return self.render_to_response(context)


########################################################################################################################
# SUBLISTS
########################################################################################################################
########################################################################################################################
# Character
########################################################################################################################


class CharacterSublistMixin(SublistMixin):
    parent_field = "characters"
    parent_model = models.Character
    last_page_url_name = None
    last_page_name = None

    def get_breadcrumb(self):
        character = self.get_object()
        return [
            {'url': reverse_lazy("site-character-list"), 'text': 'Characters'},
            {'url': reverse_lazy("site-character-detail", args=(character.slug,)), 'text': character.name},
            {'url': reverse_lazy(self.last_page_url_name, args=(character.slug,)), 'text': self.last_page_name},
        ]


class CharacterEventListView(CharacterSublistMixin, EventListView):
    last_page_url_name = "site-character-events"
    last_page_name = "Events"


class CharacterTitleListView(CharacterSublistMixin, TitleListView):
    last_page_url_name = "site-character-titles"
    last_page_name = "Titles"


class CharacterIssueListView(CharacterSublistMixin, IssueListView):
    last_page_url_name = "site-character-issues"
    last_page_name = "Issues"


########################################################################################################################
# Creator
########################################################################################################################


class CreatorSublistMixin(SublistMixin):
    parent_field = "creators"
    parent_model = models.Creator
    last_page_url_name = None
    last_page_name = None

    def get_breadcrumb(self):
        creator = self.get_object()
        return [
            {'url': reverse_lazy("site-creator-list"), 'text': 'Creators'},
            {'url': reverse_lazy("site-creator-detail", args=(creator.slug,)), 'text': creator.name},
            {'url': reverse_lazy(self.last_page_url_name, args=(creator.slug,)), 'text': self.last_page_name},
        ]


class CreatorEventListView(CreatorSublistMixin, EventListView):
    last_page_url_name = "site-creator-events"
    last_page_name = "Events"


class CreatorTitleListView(CreatorSublistMixin, TitleListView):
    last_page_url_name = "site-creator-titles"
    last_page_name = "Titles"


class CreatorIssueListView(CreatorSublistMixin, IssueListView):
    last_page_url_name = "site-creator-issues"
    last_page_name = "Issues"


########################################################################################################################
# Event
########################################################################################################################


class EventSublistMixin(SublistMixin):
    parent_field = "events"
    parent_model = models.Event
    last_page_url_name = None
    last_page_name = None

    def get_breadcrumb(self):
        event = self.get_object()
        return [
            {'url': reverse_lazy("site-event-list"), 'text': 'Events'},
            {'url': reverse_lazy("site-event-detail", args=(event.slug,)), 'text': event.name},
            {'url': reverse_lazy(self.last_page_url_name, args=(event.slug,)), 'text': self.last_page_name},
        ]


class EventTitleListView(EventSublistMixin, TitleListView):
    last_page_url_name = "site-event-titles"
    last_page_name = "Titles"


class EventIssueListView(EventSublistMixin, IssueListView):
    last_page_url_name = "site-event-issues"
    last_page_name = "Issues"


########################################################################################################################
# Issue
########################################################################################################################
########################################################################################################################
# Publisher
########################################################################################################################


class PublisherSublistMixin(SublistMixin):
    parent_field = "publisher"
    parent_model = models.Publisher
    last_page_url_name = None
    last_page_name = None

    def get_breadcrumb(self):
        publisher = self.get_object()
        return [
            {'url': reverse_lazy("site-publisher-list"), 'text': 'Publishers'},
            {'url': reverse_lazy("site-publisher-detail", args=(publisher.slug,)), 'text': publisher.name},
            {'url': reverse_lazy(self.last_page_url_name, args=(publisher.slug,)), 'text': self.last_page_name},
        ]


class PublisherEventListView(PublisherSublistMixin, EventListView):
    last_page_url_name = "site-publisher-events"
    last_page_name = "Events"


class PublisherUniverseListView(PublisherSublistMixin, UniverseListView):
    last_page_url_name = "site-publisher-universes"
    last_page_name = "Universes"


class PublisherTitleListView(PublisherSublistMixin, TitleListView):
    last_page_url_name = "site-publisher-titles"
    last_page_name = "Titles"


class PublisherIssueListView(PublisherSublistMixin, IssueListView):
    last_page_url_name = "site-publisher-issues"
    last_page_name = "Issues"
    parent_field = "title__publisher"


########################################################################################################################
# Title
########################################################################################################################


class TitleSublistMixin(SublistMixin):
    parent_field = "title"
    parent_model = models.Title
    last_page_url_name = None
    last_page_name = None

    def get_breadcrumb(self):
        title = self.get_object()
        return [
            {'url': reverse_lazy("site-title-list"), 'text': 'Titles'},
            {'url': reverse_lazy("site-title-detail", args=(title.slug,)), 'text': title.name},
            {'url': reverse_lazy(self.last_page_url_name, args=(title.slug,)), 'text': self.last_page_name},
        ]


class TitleIssueListView(TitleSublistMixin, IssueListView):
    last_page_url_name = "site-title-issues"
    last_page_name = "Issues"


########################################################################################################################
# Universe
########################################################################################################################


class UniverseSublistMixin(SublistMixin):
    parent_field = "universe"
    parent_model = models.Universe
    last_page_url_name = None
    last_page_name = None

    def get_breadcrumb(self):
        universe = self.get_object()
        return [
            {'url': reverse_lazy("site-universe-list"), 'text': 'Universes'},
            {'url': reverse_lazy("site-universe-detail", args=(universe.slug,)), 'text': universe.name},
            {'url': reverse_lazy(self.last_page_url_name, args=(universe.slug,)), 'text': self.last_page_name},
        ]


class UniverseTitleListView(UniverseSublistMixin, TitleListView):
    last_page_url_name = "site-universe-titles"
    last_page_name = "Titles"


class UniverseIssueListView(UniverseSublistMixin, IssueListView):
    last_page_url_name = "site-universe-issues"
    last_page_name = "Issues"
    parent_field = "title__universe"


########################################################################################################################
# API
########################################################################################################################


class PaginationClass(PageNumberPagination):
    """
    Common Pagination Class
    """
    page_query_param = "page"
    page_size_query_param = "page_size"
    page_size = 10


########################################################################################################################
# API Views
########################################################################################################################


class GenerateTokenView(LoginView):
    def post(self, request, format=None):
        token_ttl = self.get_token_ttl()
        token = AuthToken.objects.create(request.user, token_ttl)
        try:
            app_name = request.data['app_name']
        except KeyError:
            return Response({'status': 'error', 'error': 'App name should be not empty'})
        try:
            description = request.data['description']
        except KeyError:
            description = ''
        app_token = models.AppToken(token=token, app_name=app_name, description=description, user=request.user)
        try:
            app_token.validate_unique()
            app_token.save()
        except ValidationError:
            old_app_token = models.AppToken.objects.get(user=request.user, app_name=app_name)
            AuthToken.objects.get(token_key=old_app_token.token[:CONSTANTS.TOKEN_KEY_LENGTH]).delete()
            old_app_token.delete()
            app_token.save()
            return Response({'status': 'updated', 'token': token})

        return Response({
            'status': 'created',
            'token': token
        })


class AppTokenViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    """
    App Token control API

    list:
    App token list

    Returns all API tokens, created by user
    """
    serializer_class = serializers.AppTokenSerializer
    filter_backends = (OrderingFilter, DjangoFilterBackend)
    filterset_class = filtersets.AppTokenFilter
    ordering_fields = ("app_name",)
    ordering = ("app_name",)

    def get_queryset(self):
        return self.request.user.app_tokens.all()

    @staticmethod
    def generate_token(request):
        token_ttl = knox_settings.TOKEN_TTL
        token = AuthToken.objects.create(request.user, token_ttl)
        return token

    # TODO: add actual params and response format to docs
    @action(detail=False, methods=["post"])
    def generate(self, request):
        """
        Generate token

        Generates new app token
        """
        token = self.generate_token(request)
        try:
            app_name = request.data['app_name']
        except KeyError:
            return Response({'status': 'error', 'error': 'App name should be not empty'})
        try:
            description = request.data['description']
        except KeyError:
            description = ''
        app_token = models.AppToken(token=token, app_name=app_name, description=description, user=request.user)
        try:
            app_token.validate_unique()
            app_token.save()
        except ValidationError:
            return Response({'status': 'error', 'error': "You already created token with app_name '%s'" % app_name},
                            status=409)

        return Response({
            'status': 'created',
            'token': token,
            'app_name': app_name,
            'description': description
        })

    # TODO: add actual params and response format to docs
    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk):
        token = self.generate_token(request)
        app_token = models.AppToken.objects.get(pk=pk)
        old_token = app_token.token[:CONSTANTS.TOKEN_KEY_LENGTH]
        AuthToken.objects.get(token_key=old_token).delete()
        app_token.token = token
        app_token.save()
        return Response({
            'status': 'regenerated',
            'token': token,
            'app_name': app_token.app_name,
            'description': app_token.description
        })

    # TODO: add actual params and response format to docs
    @action(detail=True, methods=["post"])
    def revoke(self, request, pk):
        app_token = models.AppToken.objects.get(pk=pk)
        AuthToken.objects.get(token_key=app_token.token[:CONSTANTS.TOKEN_KEY_LENGTH]).delete()
        app_token.delete()
        return Response({
            'status': 'deleted',
            'token': app_token.token,
            'app_name': app_token.app_name,
            'description': app_token.description
        })

    # TODO: add actual params and response format to docs
    @action(detail=False, methods=["post"])
    def revoke_all(self, request):
        for app_token in self.request.user.app_tokens.all():
            AuthToken.objects.get(token_key=app_token.token[:CONSTANTS.TOKEN_KEY_LENGTH]).delete()
        self.request.user.app_tokens.all().delete()
        return Response({
            'status': 'all tokens deleted',
        })


class ComicsDBBaseViewSet(ReadOnlyModelMultipleSettingsViewSet):
    """
    Customized ViewSet which uses different serializer for different actions.

    Usage:
    For  usage tips look at SettingsSetGenericAPIView and Filter Backends implementation above
    """
    serializer_classes = None
    filterset_classes = None
    pagination_class = PaginationClass
    filter_backends = (MultipleSettingsOrderingFilter, FilterBackend,)


class PublisherViewSet(ComicsDBBaseViewSet):
    """
    Publisher info view

    list:
    Publisher list

    Return publisher list.
    By default ordered by `name` with `page_size` = 10

    Available ordering keys:
      * `name` - Publisher name

    retrieve:
    Publisher detail

    Return publisher detail by `id`
    """
    serializer_classes = {
        'list': serializers.PublisherListSerializer,
        'retrieve': serializers.PublisherDetailSerializer,
        'universes': serializers.UniverseListSerializer,
        'titles': serializers.TitleListSerializer
    }
    filterset_classes = {
        'list': filtersets.PublisherFilter,
        'titles': filtersets.TitleFilter
    }
    ordering_fields_set = {
        'list': (("name", "Publisher name"),),
        'universes': (("name", "Universe name"),),
        'titles': (("universe__name", "Universe name"), ("title_type__name", "Title type"), ("name", "Title name"))
    }
    ordering_set = {
        'list': ("name",),
        'universe': ("name",),
        'titles': ("universe__name", "title_type__name", "name")
    }
    queryset = models.Publisher.objects.all()

    @action(detail=True)
    def universes(self, request, pk=None):
        """
        Get publisher universes

        Return universes of publisher with specified `id`.
        By default ordered by `name` with `page_size` = 10

        Available ordering keys:
          * `name` - Universe name

        For full list of parameters see `/universe` documentation
        """
        publisher = get_object_or_404(models.Publisher, pk=pk)
        universes = publisher.universes.all()
        universes = self.filter_queryset(universes)
        return self.get_response(universes, True)

    @action(detail=True)
    def titles(self, request, pk):
        """
        Get publisher titles

        Return titles of publisher with specified `id`.
        By default ordered by `universe__name`, `title_type__name`, `name` with `page_size` = 10

        Available ordering keys:
          * ``universe__name`` - Universe name
          * ``title_type__name`` - Title type
          * ``name`` - Title name

        For full list of parameters see `/title` documentation
        """
        publisher = get_object_or_404(models.Publisher, pk=pk)
        titles = publisher.titles.all()
        titles = self.filter_queryset(titles)
        return self.get_response(titles, True)


class UniverseViewSet(ComicsDBBaseViewSet):
    """
    Universe info view

    list:
    Universes list

    Return universes list.
    By default ordered by `publisher__name`, and `name` with `page_size` = 10

    Available ordering keys:
      * `publisher__name` - Publisher name
      * `name` - Universe name

    retrieve:
    Universe detail

    Return universe detail by `id`
    """
    serializer_classes = {
        'list': serializers.UniverseListSerializer,
        'retrieve': serializers.UniverseDetailSerializer,
        'titles': serializers.TitleListSerializer
    }
    queryset = models.Universe.objects.all()
    filterset_classes = {
        'list': filtersets.UniverseFilter,
        'titles': filtersets.TitleFilter
    }
    ordering_fields_set = {
        'list': (("publisher__name", "Publisher name"), ("name", "Universe name")),
        'titles': (("title_type__name", "Title type"), ("name", "Title name"))
    }
    ordering_set = {
        'list': ("publisher__name", "name"),
        'titles': ("name",)
    }

    @action(detail=True)
    def titles(self, request, pk):
        """
        Get universe titles

        Return titles of universe with specified `id`.
        By default ordered by `name` with `page_size` = 10

        Available ordering keys:
          * `title_type__name` - Title type
          * `name` - Title name

        For full list of parameters see `/title` documentation
        """
        universe = get_object_or_404(models.Universe, pk=pk)
        titles = self.filter_queryset(universe.titles.all())
        return self.get_response(titles, True)


class TitleViewSet(ComicsDBBaseViewSet):
    """
    Title info view

    list:
    Titles list

    Return titles list.
    By default ordered by `publisher__name`, `universe__name` and `name` with `page_size` = 10

    Available ordering keys:

      * `publisher__name` - Publisher name
      * `universe__name` - Universe name
      * `title_type__name` - Title type
      * `name` - Title name

    retrieve:
    Title detail

    Return title detail by `id`
    """
    serializer_classes = {
        'list': serializers.TitleListSerializer,
        'retrieve': serializers.TitleDetailSerializer,
        'issues': serializers.IssueListSerializer
    }
    queryset = models.Title.objects.all()
    filterset_classes = {
        'list': filtersets.TitleFilter,
        'issues': filtersets.IssueFilter
    }
    ordering_fields_set = {
        'list': (("publisher__name", "Publisher name"), ("universe__name", "Universe name"),
                 ("title_type__name", "Title type"), ("name", "Title name")),
        'issues': (("name", "Issue name"), ("number", "Issue number"), ("publish_date", "Publish date"))

    }
    ordering_set = {
        'list': ("publisher__name", "universe__name", "name"),
        'issues': ("publish_date", "number")
    }

    @action(detail=True, name="Title's Issues")
    def issues(self, request, pk):
        """
        Title issues

        Return issues of title with specified `id`
        By default ordered by `publish_date`, and `number` with `page_size` = 10

        Available ordering keys:
          * `name` - Issue name
          * `number` - Issue number
          * `publish_date` - Publish date

        For full list of parameters see `/issue` documentation
        """
        title = get_object_or_404(models.Title, pk=pk)
        titles = title.issues.all()
        titles = self.filter_queryset(titles)
        return self.get_response(titles, True)

    @action(detail=True, name="Set api series", methods=['post'])
    def set_api_series(self, request, pk):
        db_title = get_object_or_404(models.Title, pk=pk)
        api_series = get_object_or_404(models.MarvelAPISeries, id=request.data['api_series_id'])
        db_title.api_series = api_series
        db_title.fill_from_marvel_api(api_series)
        db_title.save()
        try:
            run_detail = models.MarvelAPITitleMergeParserRunDetail.objects.get(id=request.data['run_detail_id'])
            run_detail.merge_result = 'MANUAL'
            run_detail.api_title = api_series
            run_detail.save()
        except Exception:
            pass
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class IssueViewSet(ComicsDBBaseViewSet):
    """
    Issue info view

    list:
    Issues list

    Return issues list.
    By default ordered by `title__publisher__name`, `title__universe__name`, `title__name`, `publish_date` and `number`\
    with `page_size` = 10

    Available ordering keys:
      * `title__publisher__name` - Publisher name
      * `title__universe__name` - Universe name
      * `title__title_type__name` - Title type
      * `title__name` - Title name
      * `publish_date` - Publish date
      * `number` - Issue number

    retrieve:
    Issue detail

    Return issue detail by `id`
    """
    serializer_classes = {
        'list': serializers.IssueListSerializer,
        'retrieve': serializers.IssueDetailSerializer,
        'set_api_series': serializers.IssueDetailSerializer,
    }
    queryset = models.Issue.objects.all()
    filterset_classes = {
        'list': filtersets.IssueFilter
    }
    ordering_fields_set = {
        'list': (("title__publisher__name", "Publisher name"), ("title__universe__name", "Universe name"),
                 ("title__title_type__name", "Title type"), ("title__name", "Title name"),
                 ("publish_date", "Publish date"), ("number", "Issue number"))
    }
    ordering_set = {
        'list': ("title__publisher__name", "title__universe__name", "title__name", "publish_date", "number")
    }

    @action(detail=True, name="Set api comic", methods=['post'])
    def set_api_comic(self, request, pk):
        db_issue = get_object_or_404(models.Issue, pk=pk)
        api_comic = get_object_or_404(models.MarvelAPIComics, id=request.data['api_comic_id'])
        db_issue.marvel_api_comic = api_comic
        db_issue.fill_from_marvel_api(api_comic)
        db_issue.save()
        try:
            run_detail = models.MarvelAPIIssueMergeParserRunDetail.objects.get(id=request.data['run_detail_id'])
            run_detail.merge_result = 'MANUAL'
            run_detail.api_comic = api_comic
            run_detail.save()
        except Exception:
            pass
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class ParserRunViewSet(ComicsDBBaseViewSet):
    """
    Parser Run info view

    list:
    Parser runs list

    Return list of all parser runs.
    By default ordered by `start` descending with page size = 10

    Available ordering keys:
      * parser_name - Parser
      * status_name - Status
      * start - Start date and time
      * end - End date and time

    retrieve:
    Parser run detail

    Return parser run by `id`
    """
    permission_classes = (IsAdminUser,)
    queryset = models.ParserRun.objects.all()
    serializer_classes = {
        'list': serializers.ParserRunListSerializer,
        'retrieve': serializers.ParserRunDetailSerializer,
        'details_cloud': serializers.CloudFilesParserRunDetailListSerializer,
        'details_marvel_api': serializers.MarvelAPIParserRunDetailListSerializer,
        'details_marvel_api_creator_merge': serializers.MarvelAPICreatorMergeRunDetailListSerializer,
        'details_marvel_api_character_merge': serializers.MarvelAPICharacterMergeRunDetailListSerializer,
        'details_marvel_api_event_merge': serializers.MarvelAPIEventMergeRunDetailListSerializer,
        'details_marvel_api_title_merge': serializers.MarvelAPITitleMergeRunDetailListSerializer,
        'details_marvel_api_issue_merge': serializers.MarvelAPIIssueMergeRunDetailListSerializer,

    }
    filterset_classes = {
        'list': filtersets.ParserRunFilter,
        'details_cloud': filtersets.CloudFilesParserRunDetailFilter,
        'details_marvel_api': filtersets.MarvelAPIParserRunDetailFilter,
        'details_marvel_api_creator_merge': filtersets.MarvelAPICreatorMergeRunDetailFilter,
        'details_marvel_api_character_merge': filtersets.MarvelAPICharacterMergeRunDetailFilter,
        'details_marvel_api_event_merge': filtersets.MarvelAPIEventMergeRunDetailFilter,
        'details_marvel_api_title_merge': filtersets.MarvelAPITitleMergeRunDetailFilter,
        'details_marvel_api_issue_merge': filtersets.MarvelAPIIssueMergeRunDetailFilter,
    }
    ordering_fields_set = {
        'list': (("parser", "Parser"), ("status", "Status"), ("start", "Start date and time"),
                 ("end", "End date and time"),),
        'details_cloud': (("status_name", "Status"), ("start", "Start date and time"), ("end", "End date and time"),
                          ("file_key", "File key in DO cloud")),
        'details_marvel_api': (
            ("status_name", "Status"), ("start", "Start date and time"), ("end", "End date and time"),
            ("action", "Action type"), ("entity_type", "Entity type"), ("entity_id", "Entity ID")),
        'details_marvel_api_creator_merge': ("start", "end", "status", "api_creator__full_name", "db_creator__name"),
        'details_marvel_api_character_merge': ("start", "end", "status", "api_character__name", "db_character__name"),
        'details_marvel_api_event_merge': ("start", "end", "status", "api_event__title", "db_event__name"),
        'details_marvel_api_title_merge': ("start", "end", "status", "api_title__title", "db_title__name"),
        'details_marvel_api_issue_merge': ("start", "end", "status", "api_comic__title", "db_issue__name"),
    }
    ordering_set = {
        'list': ("-start",),
        'details_cloud': ('-start',),
        'details_marvel_api': ('-start',),
        'details_marvel_api_creator_merge': ('-start',),
        'details_marvel_api_character_merge': ('-start',),
        'details_marvel_api_event_merge': ('-start',),
        'details_marvel_api_title_merge': ('-start',),
        'details_marvel_api_issue_merge': ('-start',),
    }

    @action(detail=True, name="Parser run details")
    def details(self, request, pk):
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser in ('CLOUD_FILES', 'MARVEL_API', 'MARVEL_API_CREATOR_MERGE', 'MARVEL_API_CHARACTER_MERGE',
                          'MARVEL_API_EVENT_MERGE', 'MARVEL_API_TITLE_MERGE', 'MARVEL_API_ISSUE_MERGE'):
            return HttpResponseRedirect(run.run_details_url)
        raise Http404

    @action(detail=True, name="Cloud Parser Run details")
    def details_cloud(self, request, pk):
        """
        Cloud Parser Run details

        Return details of cloud parser's run with specified `id`. If this is not cloud parser's run, returns HTTP404
        By default ordered by `start` descending with `page_size` = 10

        Available ordering keys:
          * `status_name` - Status
          * `start` - Start date and time
          * `end` - End date and time
          * `file_key - File key in DO cloud")
        """
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser != 'CLOUD_FILES':
            raise Http404
        details = run.cloudfilesparserrundetails.all()
        details = self.filter_queryset(details)
        return self.get_response(details, True)

    @action(detail=True, name="Marvel API Parser Run details")
    def details_marvel_api(self, request, pk):
        """
        Marvel API Parser Run details

        Return details of Marvel API parser's run with specified `id`. If this is not Marvel API parser's run, returns
        HTTP404.
        By default ordered by `start` descending with `page_size` = 10

        Available ordering keys:
          * `status_name` - Status
          * `start` - Start date and time
          * `end` - End date and time
          * `action` - Action (get or process)
        """
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser != 'MARVEL_API':
            raise Http404
        details = run.marvelapiparserrundetails.all()
        details = self.filter_queryset(details)
        return self.get_response(details, True)

    @action(detail=True, name="Marvel API Creator merge details")
    def details_marvel_api_creator_merge(self, request, pk):
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser != 'MARVEL_API_CREATOR_MERGE':
            raise Http404
        details = run.marvelapicreatormergeparserrundetails.all().select_related("api_creator", "db_creator")
        details = self.filter_queryset(details)
        return self.get_response(details, True)

    @action(detail=True, name="Marvel API character merge details")
    def details_marvel_api_character_merge(self, request, pk):
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser != 'MARVEL_API_CHARACTER_MERGE':
            raise Http404
        details = run.marvelapicharactermergeparserrundetails.all().select_related("api_character", "db_character")
        details = self.filter_queryset(details)
        return self.get_response(details, True)

    @action(detail=True, name="Marvel API event merge details")
    def details_marvel_api_event_merge(self, request, pk):
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser != 'MARVEL_API_EVENT_MERGE':
            raise Http404
        details = run.marvelapieventmergeparserrundetails.all().select_related("api_event", "db_event")
        details = self.filter_queryset(details)
        return self.get_response(details, True)

    @action(detail=True, name="Marvel API title merge details")
    def details_marvel_api_title_merge(self, request, pk):
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser != 'MARVEL_API_TITLE_MERGE':
            raise Http404
        details = run.marvelapititlemergeparserrundetails.all().select_related("api_title", "db_title")
        details = self.filter_queryset(details)
        return self.get_response(details, True)

    @action(detail=True, name="Marvel API issue merge details")
    def details_marvel_api_issue_merge(self, request, pk):
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser != 'MARVEL_API_ISSUE_MERGE':
            raise Http404
        details = run.marvelapiissuemergeparserrundetails.all().select_related("api_comic", "db_issue")
        details = self.filter_queryset(details)
        return self.get_response(details, True)


class MarvelAPISeriesViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = models.MarvelAPISeries.objects.all()
    permission_classes = (IsAdminUser,)
    serializer_class = serializers.MarvelAPISeriesSerializer
    filter_backends = (OrderingFilter, DjangoFilterBackend)
    filterset_class = filtersets.MarvelAPISeriesFilter
    pagination_class = PaginationClass
    ordering_fields = ("id", "title", "start_year", "end_year", "rating", "series_type")
    ordering = ("title", "start_year")

    @action(detail=True, name="Toggle Marvel API series ignore flag", methods=["post"])
    def toggle_ignore(self, request, pk):
        series = get_object_or_404(models.MarvelAPISeries, pk=pk)
        series.ignore = not series.ignore
        series.save()
        return Response(status=status.HTTP_200_OK)


class MarvelAPIComicsViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = models.MarvelAPIComics.objects.all()
    permission_classes = (IsAdminUser,)
    serializer_class = serializers.MarvelAPIComicsSerializer
    filter_backends = (OrderingFilter, DjangoFilterBackend)
    filterset_class = filtersets.MarvelAPIComicsFilter
    pagination_class = PaginationClass
    ordering_fields = ("id", "title", "issue_number", "page_count", "description")
    ordering = ("title", "issue_number")


class CloudFilesParserRunDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.CloudFilesParserRunDetail.objects.all()
    serializer_class = serializers.CloudFilesParserRunDetailDetailSerializer


class MarvelAPIParserRunDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.MarvelAPIParserRunDetail.objects.all()
    serializer_class = serializers.MarvelAPIParserRunDetailDetailSerializer


class MarvelAPICreatorMergeRunDetailDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.MarvelAPICreatorMergeParserRunDetail.objects.all()
    serializer_class = serializers.MarvelAPICreatorMergeRunDetailDetailSerializer


class MarvelAPICharacterMergeRunDetailDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.MarvelAPICharacterMergeParserRunDetail.objects.all()
    serializer_class = serializers.MarvelAPICharacterMergeRunDetailListSerializer


class MarvelAPIEventMergeRunDetailDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.MarvelAPIEventMergeParserRunDetail.objects.all()
    serializer_class = serializers.MarvelAPIEventMergeRunDetailDetailSerializer


class MarvelAPITitleMergeRunDetailDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.MarvelAPITitleMergeParserRunDetail.objects.all()
    serializer_class = serializers.MarvelAPITitleMergeRunDetailDetailSerializer


class MarvelAPIIssueMergeRunDetailDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.MarvelAPIIssueMergeParserRunDetail.objects.all()
    serializer_class = serializers.MarvelAPIIssueMergeRunDetailDetailSerializer


class ParserScheduleViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin,
                            mixins.UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = PeriodicTask.objects.filter(task='comics_db.tasks.parser_run_task')
    serializer_class = serializers.ParserScheduleSerializer
    filter_backends = (OrderingFilter,)
    ordering_fields = ("name", "enabled", "last_run_at")

    def create(self, request, *args, **kwargs):
        try:
            # Task info
            name = request.data['task-name']
            if not name:
                return Response({'status': 'error', 'message': 'Task name can\'t be empty'})
            desc = request.data['task-desc']

            # Parser
            parser = request.data['parser']
            if parser == 'CLOUD_FILES':
                path_root = request.data['cloud-path-root']
                if not path_root:
                    return JsonResponse({'status': 'error', 'message': 'Path root should be specified'})
                full = bool(request.POST['cloud-full'])
                load_covers = bool(request.POST['cloud-load-cover'])
                marvel_api_merge = bool(request.POST['cloud-marvel-api-merge'])
                init_args = (path_root, full, load_covers)
                task = 'comics_db.tasks.parser_run_task'
                task_args = json.dumps((parser, init_args))
            elif parser == 'MARVEL_API':
                incremental = request.POST['marvel-api-incremental']
                init_args = (incremental,)
                task = 'comics_db.tasks.parser_run_task'
                task_args = json.dumps((parser, init_args))
            elif parser in ("MARVEL_API_CREATOR_MERGE",
                            "MARVEL_API_CHARACTER_MERGE",
                            "MARVEL_API_EVENT_MERGE",
                            "MARVEL_API_TITLE_MERGE",
                            "MARVEL_API_ISSUE_MERGE"):
                task = 'comics_db.tasks.parser_run_task'
                task_args = json.dumps((parser, []))
            elif parser == "FULL_MARVEL_API_MERGE":
                task = 'comics_db.tasks.parser_run_task'
                task_args = json.dumps((parser, []))
            else:
                return Response({'status': 'error', 'message': 'Unknown parser code "%s"' % parser})

            # Schedule
            schedule_type = request.data['schedule_type']
            if schedule_type == 'INTERVAL':
                try:
                    every = int(request.data['interval__every'])
                except ValueError:
                    return Response({'status': 'error', 'message': 'Parameter "Every" should be integer number'})
                period = request.data['interval__period']
                schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=every,
                    period=period
                )
                PeriodicTask.objects.create(
                    interval=schedule,
                    task='comics_db.tasks.parser_run_task',
                    args=task_args,
                    name=name,
                    description=desc
                )
            elif schedule_type == 'CRON':
                minute = request.data['crontab__minute'] or '*'
                hour = request.data['crontab__hour'] or '*'
                day_of_week = request.data['crontab__day_of_week'] or '*'
                day_of_month = request.data['crontab__day_of_month'] or '*'
                month_of_year = request.data['crontab__month_of_year'] or '*'

                schedule, _ = CrontabSchedule.objects.get_or_create(
                    minute=minute,
                    hour=hour,
                    day_of_week=day_of_week,
                    day_of_month=day_of_month,
                    month_of_year=month_of_year
                )
                PeriodicTask.objects.create(
                    crontab=schedule,
                    task=task,
                    args=task_args,
                    name=name,
                    description=desc
                )
            else:
                return Response({'status': 'error', 'message': 'Unknown schedule type "%s"' % schedule_type})

            return Response({'status': 'created', 'message': 'Schedule created'}, status=status.HTTP_201_CREATED)
        except KeyError as err:
            return Response({'status': 'error', 'message': 'Parameter "%s" not found' % err})
        except Exception as err:
            return Response({'status': 'error', 'message': err.args[0]})
