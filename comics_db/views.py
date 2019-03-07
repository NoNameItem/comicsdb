from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_multiple_settings.filter_backends.django_filters import FilterBackend
from drf_multiple_settings.viewsets import ReadOnlyModelMultipleSettingsViewSet, MultipleSettingsOrderingFilter
from knox.models import AuthToken
from knox.views import LoginView
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from knox.settings import CONSTANTS, knox_settings

from comics_db import models, serializers, filtersets


########################################################################################################################
# Site
########################################################################################################################


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
    ordering_fields = ("app_name", )
    ordering = ("app_name", )

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
        'details_cloud': serializers.CloudFilesParserRunDetailListSerializer
    }
    filterset_classes = {
        'list': filtersets.ParserRunFilter,
        'details_cloud': filtersets.CloudFilesParserRunDetailFilter
    }
    ordering_fields_set = {
        'list': (("parser_name", "Parser"), ("status_name", "Status"), ("start", "Start date and time"),
                 ("end", "End date and time"),),
        'details_cloud': (("status_name", "Status"), ("start", "Start date and time"), ("end", "End date and time"),
                          ("file_key", "File key in DO cloud"))
    }
    ordering_set = {
        'list': ("-start",),
        'details_cloud': ('-start',)
    }

    @action(detail=True, name="Parser run details")
    def details(self, request, pk):
        run = get_object_or_404(models.ParserRun, pk=pk)
        if run.parser == 'CLOUD_FILES':
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


class CloudFilesParserRunDetailViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAdminUser,)
    queryset = models.CloudFilesParserRunDetail.objects.all()
    serializer_class = serializers.CloudFilesParserRunDetailDetailSerializer
