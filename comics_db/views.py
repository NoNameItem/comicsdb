import datetime
import json
import math
import os
from zipfile import ZIP_DEFLATED

import boto3
import zipstream
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError
from django.db.models import Count, Q, Max, Case, When, F, Window
from django.db.models.functions import RowNumber
from django.http import Http404, HttpResponseRedirect, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
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
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from knox.settings import CONSTANTS, knox_settings
from el_pagination.views import AjaxListView
from smart_open import open as sm_open

from comics_db import models, serializers, filtersets, tasks, forms

########################################################################################################################
# Site
########################################################################################################################


########################################################################################################################
# Main Page
########################################################################################################################
from comics_db.models import ReadingListIssue
from comics_db.issue_archive import S3FileWrapper, construct_archive
from comicsdb import settings


class MainPageView(TemplateView):
    template_name = "comics_db/main_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titles_count'] = models.Title.objects.count()
        context['issues_count'] = models.Issue.objects.count()
        context['publishers_count'] = models.Publisher.objects.count()
        context['universes_count'] = models.Universe.objects.count()
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
# Publisher
########################################################################################################################


class PublisherListView(ListView):
    template_name = "comics_db/publisher/list.html"
    queryset = models.Publisher.objects.all()
    context_object_name = "publishers"


class PublisherDetailView(DetailView):
    template_name = "comics_db/publisher/detail.html"
    model = models.Publisher
    context_object_name = "publisher"

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

    def post(self, request, slug):
        if not self.request.user.is_staff:
            raise PermissionDenied
        self.object = self.get_object()
        form = forms.PublisherForm(request.POST, request.FILES)
        if form.is_valid():
            self.object.logo = form.cleaned_data['logo'] or self.object.logo
            self.object.poster = form.cleaned_data['poster'] or self.object.poster
            self.object.desc = form.cleaned_data['desc']
            self.object.save()
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)


class PublisherUniverseListView(AjaxListView):
    template_name = "comics_db/publisher/universe_list.html"
    context_object_name = "universes"
    page_template = "comics_db/publisher/universe_list_block.html"

    def get_queryset(self):
        self.publisher = models.Publisher.objects.get(slug=self.kwargs['slug'])
        return models.Universe.objects.filter(publisher=self.publisher)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['publisher'] = self.publisher
        return context


class PublisherTitleListView(AjaxListView):
    template_name = "comics_db/publisher/title_list.html"
    context_object_name = "titles"
    page_template = "comics_db/publisher/title_list_block.html"
    search_fields = ('name__icontains', 'title_type__name__icontains', 'universe__name__icontains')

    def get_queryset(self):
        self.publisher = models.Publisher.objects.get(slug=self.kwargs['slug'])
        queryset = models.Title.objects.filter(publisher=self.publisher).annotate(issue_count=Count('issues')). \
            select_related("universe", "title_type")
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                read_issue_count=Count('issues', filter=Q(issues__readers=self.request.user.profile)))
        search = self.request.GET.get('search', "")
        if search:
            q = Q()
            for field in self.search_fields:
                q = q | Q(**{field: search})
            queryset = queryset.filter(q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['publisher'] = self.publisher
        context['search'] = self.request.GET.get('search', "")
        return context


class PublisherIssueListView(AjaxListView):
    template_name = "comics_db/publisher/issue_list.html"
    page_template = "comics_db/publisher/issue_list_block.html"
    context_object_name = "issues"

    search_fields = ('name__icontains', 'title__name__icontains', 'title__title_type__name__icontains',
                     'title__universe__name__icontains')

    def get_queryset(self):
        self.publisher = models.Publisher.objects.get(slug=self.kwargs['slug'])
        queryset = models.Issue.objects.filter(title__publisher=self.publisher).select_related("title__universe",
                                                                                               "title__title_type")
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(read=Count('readers', filter=Q(readers=self.request.user.profile)))
        search = self.request.GET.get('search', "")
        hide_read = self.request.GET.get('hide-read')
        if hide_read == 'on':
            queryset = queryset.exclude(read=1)
        if search:
            q = Q()
            for field in self.search_fields:
                q = q | Q(**{field: search})
            queryset = queryset.filter(q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['publisher'] = self.publisher
        context['search'] = self.request.GET.get('search', "")
        context['hide_read'] = self.request.GET.get('hide-read')
        return context


########################################################################################################################
# Universe
########################################################################################################################


class UniverseListView(ListView):
    template_name = "comics_db/universe/list.html"
    queryset = models.Universe.objects.all()
    context_object_name = "universes"


class UniverseDetailView(DetailView):
    template_name = "comics_db/universe/detail.html"
    model = models.Universe
    context_object_name = "universe"

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

    def post(self, request, slug):
        if not self.request.user.is_staff:
            raise PermissionDenied
        self.object = self.get_object()
        form = forms.UniverseForm(request.POST, request.FILES)
        if form.is_valid():
            self.object.poster = form.cleaned_data['poster'] or self.object.poster
            self.object.desc = form.cleaned_data['desc']
            self.object.save()
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)


class UniverseTitleListView(AjaxListView):
    template_name = "comics_db/universe/title_list.html"
    context_object_name = "titles"
    page_template = "comics_db/universe/title_list_block.html"
    search_fields = ('name__icontains', 'title_type__name__icontains')

    def get_queryset(self):
        self.universe = models.Universe.objects.get(slug=self.kwargs['slug'])
        queryset = models.Title.objects.filter(universe=self.universe).annotate(issue_count=Count('issues')). \
            select_related("title_type")
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                read_issue_count=Count('issues', filter=Q(issues__readers=self.request.user.profile)))
        search = self.request.GET.get('search', "")
        if search:
            q = Q()
            for field in self.search_fields:
                q = q | Q(**{field: search})
            queryset = queryset.filter(q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['universe'] = self.universe
        context['search'] = self.request.GET.get('search', "")
        return context


class UniverseIssueListView(AjaxListView):
    template_name = "comics_db/universe/issue_list.html"
    page_template = "comics_db/universe/issue_list_block.html"
    context_object_name = "issues"

    search_fields = ('name__icontains', 'title__name__icontains', 'title__title_type__name__icontains',)

    def get_queryset(self):
        self.universe = models.Universe.objects.get(slug=self.kwargs['slug'])
        queryset = models.Issue.objects.filter(title__universe=self.universe).select_related("title__title_type")
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(read=Count('readers', filter=Q(readers=self.request.user.profile)))
        search = self.request.GET.get('search', "")
        hide_read = self.request.GET.get('hide-read')
        if hide_read == 'on':
            queryset = queryset.exclude(read=1)
        if search:
            q = Q()
            for field in self.search_fields:
                q = q | Q(**{field: search})
            queryset = queryset.filter(q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['universe'] = self.universe
        context['search'] = self.request.GET.get('search', "")
        context['hide_read'] = self.request.GET.get('hide-read')
        return context


########################################################################################################################
# Title
########################################################################################################################


class TitleListView(AjaxListView):
    template_name = "comics_db/title/list.html"
    context_object_name = "titles"
    page_template = "comics_db/title/list_block.html"

    search_fields = ('name__icontains', 'title_type__name__icontains', 'publisher__name__icontains',
                     'universe__name__icontains')

    def get_queryset(self):
        queryset = models.Title.objects.annotate(issue_count=Count('issues')).select_related("publisher", "universe",
                                                                                             "title_type")
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                read_issue_count=Count('issues', filter=Q(issues__readers=self.request.user.profile)))
        search = self.request.GET.get('search', "")
        if search:
            q = Q()
            for field in self.search_fields:
                q = q | Q(**{field: search})
            queryset = queryset.filter(q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', "")
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


class TitleDetailView(DetailView):
    template_name = "comics_db/title/detail.html"
    model = models.Title
    context_object_name = "title"

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

    def post(self, request, slug):
        if not self.request.user.is_staff:
            raise PermissionDenied
        self.object = self.get_object()
        form = forms.TitleForm(request.POST, request.FILES, instance=self.object)
        if form.is_valid():
            self.object = form.save()
            return HttpResponseRedirect(self.object.site_link)
        context = self.get_context_data(object=self.object)
        context['form'] = form
        return self.render_to_response(context)


class DeleteTitle(View, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, slug):
        redirect_url = request.POST.get('delete-redirect-url')
        title = models.Title.objects.get(slug=slug)
        title.delete()
        return HttpResponseRedirect(redirect_url)


class MoveTitleIssues(View, UserPassesTestMixin):
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


class TitleIssueListView(AjaxListView):
    template_name = "comics_db/title/issue_list.html"
    page_template = "comics_db/title/issue_list_block.html"
    context_object_name = "issues"

    search_fields = ('name__icontains',)

    def get_queryset(self):
        self.title = models.Title.objects.get(slug=self.kwargs['slug'])
        queryset = models.Issue.objects.filter(title=self.title)
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(read=Count('readers', filter=Q(readers=self.request.user.profile)))
        search = self.request.GET.get('search', "")
        hide_read = self.request.GET.get('hide-read')
        if hide_read == 'on':
            queryset = queryset.exclude(read=1)
        if search:
            q = Q()
            for field in self.search_fields:
                q = q | Q(**{field: search})
            queryset = queryset.filter(q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['search'] = self.request.GET.get('search', "")
        context['hide_read'] = self.request.GET.get('hide-read')
        return context


class AddTitleToReadingList(View, LoginRequiredMixin):
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
            order = ReadingListIssue.objects.filter(reading_list=reading_list).aggregate(max_order=Max('order'))[
                        'max_order'] or 0
            rl_issues = []
            for issue in issues:
                order += 1

                if issue not in added_issues:
                    rl_issue = ReadingListIssue(reading_list=reading_list, issue=issue, order=order)
                    rl_issues.append(rl_issue)

            ReadingListIssue.objects.bulk_create(rl_issues)
            return JsonResponse({'status': "success", 'issue_count': len(rl_issues),
                                 'list_name': reading_list.name})
        except models.Title.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Title not found."})
        except models.ReadingList.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Reading list not found. Please refresh page."})
        except Exception as err:
            return JsonResponse({'status': 'error', 'message': 'Unknown error, please contact administrator. \n'
                                                               'Error message: %s' % err.args[0]})


class DownloadTitle(View):
    def get(self, request, slug):
        title = get_object_or_404(models.Title, slug=slug)

        issues = list(map(lambda x: ("{0}/[{0.name}] {1}.{2}".format(title, x.name, os.path.splitext(x.link)[1]), x.link),
                          title.issues.all()))

        z = construct_archive(issues)

        response = StreamingHttpResponse(z, content_type="application/zip")
        response['Content-Disposition'] = "attachment; filename=\"{0}.zip\"".format(title)

        return response


########################################################################################################################
# Issue
########################################################################################################################


class IssueListView(AjaxListView):
    template_name = "comics_db/issue/list.html"
    context_object_name = "issues"
    page_template = "comics_db/issue/list_block.html"

    search_fields = ('name__icontains', 'title__name__icontains', 'title__title_type__name__icontains',
                     'title__publisher__name__icontains', 'title__universe__name__icontains')

    def get_queryset(self):
        queryset = models.Issue.objects.all().select_related("title__publisher", "title__universe",
                                                             "title__title_type")
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(read=Count('readers', distinct=True,
                                                    filter=Q(readers=self.request.user.profile)))
        try:
            search = self.request.GET.get('search', None)
            hide_read = self.request.GET.get('hide-read')
            if hide_read == 'on':
                queryset = queryset.exclude(read=1)
            if search:
                q = Q()
                for field in self.search_fields:
                    q = q | Q(**{field: search})
                return queryset.filter(q)
            return queryset
        except KeyError:
            return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', "")
        context['hide_read'] = self.request.GET.get('hide-read')
        return context


class IssueDetailView(DetailView):
    template_name = "comics_db/issue/detail.html"
    model = models.Issue
    context_object_name = "issue"

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

    def post(self, request, slug):
        if not self.request.user.is_staff:
            raise PermissionDenied
        self.object = self.get_object()
        form = forms.IssueForm(request.POST, request.FILES, instance=self.object)
        if form.is_valid():
            self.object = form.save()
            return HttpResponseRedirect(self.object.site_link)
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)


class DeleteIssue(View, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, slug):
        redirect_url = request.POST.get('delete-redirect-url')
        issue = models.Issue.objects.get(slug=slug)
        issue.delete()
        return HttpResponseRedirect(redirect_url)


class ReadIssue(View, LoginRequiredMixin):
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


class AddToReadingList(View, LoginRequiredMixin):
    def post(self, request, slug):
        try:
            issue = models.Issue.objects.get(slug=slug)
            reading_list = self.request.user.profile.reading_lists.get(pk=request.POST.get('list_id'))
            order = ReadingListIssue.objects.filter(reading_list=reading_list).aggregate(max_order=Max('order'))[
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
# Reading lists
########################################################################################################################


class ReadingListListView(ListView, LoginRequiredMixin):
    template_name = "comics_db/profile/list.html"
    context_object_name = "reading_lists"

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


class ReadingListDetailView(AjaxListView):
    template_name = "comics_db/profile/issue_list.html"
    context_object_name = "issues"
    page_template = "comics_db/profile/issue_list_block.html"

    search_fields = (
        'issue__name__icontains', 'issue__title__name__icontains', 'issue__title__title_type__name__icontains',
        'issue__title__publisher__name__icontains', 'issue__title__universe__name__icontains')

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

        queryset = ReadingListIssue.objects.filter(
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

    def post(self, request, slug):
        if not self.request.user.is_authenticated:
            raise PermissionDenied
        self.object = self.request.user.profile.reading_lists.get(slug=slug)
        if not self.object.owner == self.request.user.profile:
            raise PermissionDenied
        form = forms.ReadingListForm(request.POST, instance=self.object)
        if form.is_valid():
            self.object = form.save()
            return HttpResponseRedirect(self.object.site_link)
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)


class DeleteReadingList(View, LoginRequiredMixin):
    def post(self, request, slug):
        if not request.user.is_authenticated:
            raise PermissionError
        reading_list = self.request.user.profile.reading_lists.get(slug=slug)
        reading_list.delete()
        return JsonResponse({'status': 'success'})


class ChangeReadingOrder(View, LoginRequiredMixin):
    def post(self, request, slug):
        if not request.user.is_authenticated:
            raise PermissionError
        try:
            reading_list = self.request.user.profile.reading_lists.get(slug=slug)
            old_pos = int(self.request.POST['oldPos'])
            new_pos = int(self.request.POST['newPos'])
            issue_id = int(self.request.POST['issueID'])

            if old_pos < new_pos:
                ReadingListIssue.objects.filter(reading_list=reading_list, order__gt=old_pos, order__lte=new_pos) \
                    .update(order=F('order') - 1)
            else:
                ReadingListIssue.objects.filter(reading_list=reading_list, order__gte=new_pos, order__lt=old_pos) \
                    .update(order=F('order') + 1)

            rl_issue = ReadingListIssue.objects.get(reading_list=reading_list, issue_id=issue_id)
            rl_issue.order = new_pos
            rl_issue.save()

            return JsonResponse({'status': 'success'})
        except KeyError:
            return JsonResponse({'status': "error", 'message': "Can't get new order."})


class DeleteFromReadingList(View, LoginRequiredMixin):
    def post(self, request, slug):
        try:
            reading_list = request.user.profile.reading_lists.get(slug=slug)
            issue = reading_list.issues.get(pk=request.POST.get('issue_id'))
            rl_issue = ReadingListIssue.objects.get(reading_list=reading_list, issue=issue)
            order = rl_issue.order
            ReadingListIssue.objects.filter(reading_list=reading_list, order__gt=order).update(order=F("order") - 1)
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


class ReadingListIssueDetailView(DetailView):
    template_name = "comics_db/profile/reading_list_issue.html"
    context_object_name = "issue"

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
            rl_issue = ReadingListIssue.objects.get(reading_list=self.reading_list, issue=issue)
            try:
                context['previous_issue'] = ReadingListIssue.objects.get(reading_list=self.reading_list,
                                                                         order=rl_issue.order - 1).issue
            except ReadingListIssue.DoesNotExist:
                context['previous_issue'] = None

            try:
                context['next_issue'] = ReadingListIssue.objects.get(reading_list=self.reading_list,
                                                                     order=rl_issue.order + 1).issue
            except ReadingListIssue.DoesNotExist:
                context['next_issue'] = None

        else:
            issues = list(self.reading_list.issues.all())
            current_number = issues.index(issue)
            if current_number > 0:
                context['previous_issue'] = issues[current_number - 1]
            if current_number < len(issues) - 1:
                context['next_issue'] = issues[current_number + 1]

        return context

    def post(self, request, slug, list_slug):
        if not self.request.user.is_staff:
            raise PermissionDenied
        self.object = self.get_object()
        form = forms.IssueForm(request.POST, request.FILES, instance=self.object)
        if form.is_valid():
            self.object = form.save()
            return HttpResponseRedirect(reverse('site-reading-list-issue', args=(list_slug, slug)))
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)


class DownloadReadingList(View):
    def get(self, request, slug):
        rl = get_object_or_404(models.ReadingList, slug=slug)

        queryset = ReadingListIssue.objects.filter(reading_list=rl).select_related('issue', 'issue__title')

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
        # response['Content-Length'] = size

        return response


########################################################################################################################
# Parser log
########################################################################################################################


class ParserLogView(UserPassesTestMixin, TemplateView):
    def test_func(self):
        return self.request.user.is_staff


class ParserRunDetail(UserPassesTestMixin, DetailView):
    model = models.ParserRun
    context_object_name = 'parser_run'
    template_name = "comics_db/admin/parser_run.html"

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


class RunParser(UserPassesTestMixin, View):
    parser_dict = dict(models.ParserRun.PARSER_CHOICES)

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request):
        try:
            parser = request.POST['parser_code']
            args = tuple()
            if not parser or parser == 'BASE':
                return JsonResponse({'status': 'error', 'message': 'Invalid parser code "%s"' % parser})
            if parser == 'CLOUD_FILES':
                path_root = request.POST['cloud-path-root']
                if not path_root:
                    return JsonResponse({'status': 'error', 'message': 'Path root should be specified'})
                full = bool(request.POST['cloud-full'])
                load_covers = bool(request.POST['cloud-load-cover'])
                args = (path_root, full, load_covers)
            elif parser == 'MARVEL_API':
                incremental = request.POST['marvel-api-incremental']
                args = (incremental,)
            tasks.parser_run_task.delay(parser, args)
            return JsonResponse({'status': 'success', 'message': '%s started' % self.parser_dict[parser]})
        except Exception as err:
            return JsonResponse({'status': 'error', 'message': err.args[0]})


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
        'retrieve': serializers.IssueDetailSerializer
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
        'details_marvel_api_creator_merge' : serializers.MarvelAPICreatorMergeRunDetailListSerializer,
        'details_marvel_api_character_merge': serializers.MarvelAPICharacterMergeRunDetailListSerializer,

    }
    filterset_classes = {
        'list': filtersets.ParserRunFilter,
        'details_cloud': filtersets.CloudFilesParserRunDetailFilter,
        'details_marvel_api': filtersets.MarvelAPIParserRunDetailFilter,
        'details_marvel_api_creator_merge': filtersets.MarvelAPICreatorMergeRunDetailFilter,
        'details_marvel_api_character_merge': filtersets.MarvelAPICharacterMergeRunDetailFilter,
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
        'details_marvel_api_character_merge': ("start", "end", "status", "api_character__name", "db_character__name")
    }
    ordering_set = {
        'list': ("-start",),
        'details_cloud': ('-start',),
        'details_marvel_api': ('-start',),
        'details_marvel_api_creator_merge': ('-start',),
        'details_marvel_api_character_merge': ('-start',),
    }

    @action(detail=True, name="Parser run details")
    def details(self, request, pk):
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser in ('CLOUD_FILES', 'MARVEL_API', 'MARVEL_API_CREATOR_MERGE'):
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
        details = run.marvelapicreatormergeparserrundetails.all()
        details = self.filter_queryset(details)
        return self.get_response(details, True)

    @action(detail=True, name="Marvel API character merge details")
    def details_marvel_api_character_merge(self, request, pk):
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser != 'MARVEL_API_CHARACTER_MERGE':
            raise Http404
        details = run.marvelapicharactermergeparserrundetails.all()
        details = self.filter_queryset(details)
        return self.get_response(details, True)


class CloudFilesParserRunDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.CloudFilesParserRunDetail.objects.all()
    serializer_class = serializers.CloudFilesParserRunDetailDetailSerializer


class MarvelAPIParserRunDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.MarvelAPIParserRunDetail.objects.all()
    serializer_class = serializers.MarvelAPIParserRunDetailDetailSerializer


class MarvelAPICreatorMergeRunDetailDetailSerializerViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.MarvelAPICreatorMergeParserRunDetail.objects.all()
    serializer_class = serializers.MarvelAPICreatorMergeRunDetailDetailSerializer


class MarvelAPICharacterMergeRunDetailDetailSerializerViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.MarvelAPICharacterMergeParserRunDetail.objects.all()
    serializer_class = serializers.MarvelAPICharacterMergeRunDetailListSerializer


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
                init_args = (path_root, full, load_covers)
                task_args = json.dumps((parser, init_args))
            elif parser == 'MARVEL_API':
                incremental = request.POST['marvel-api-incremental']
                init_args = (incremental,)
                task_args = json.dumps((parser, init_args))
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
                    task='comics_db.tasks.parser_run_task',
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
