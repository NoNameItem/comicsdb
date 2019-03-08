# Serializer for use in django-rest-framework views
from rest_framework import serializers

from comics_db import models
from comicsdb import settings


# Common serializer's settings for list view. Show only id, url to detail and name. Needs to be subclassed with
# needed Meta.model


class ListSerializer(serializers.HyperlinkedModelSerializer):
    name_long = serializers.CharField(source="__str__", read_only=True, help_text="Representative name")

    class Meta:
        fields = ("id", settings.REST_FRAMEWORK["URL_FIELD_NAME"], "name_long")
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            settings.REST_FRAMEWORK["URL_FIELD_NAME"]: {'help_text': "Link to detail API endpoint"}
        }


# Publisher


class PublisherListSerializer(ListSerializer):
    class Meta(ListSerializer.Meta):
        model = models.Publisher


class PublisherDetailSerializer(serializers.HyperlinkedModelSerializer):
    universes = serializers.HyperlinkedIdentityField(
        view_name='publisher-universes',
        help_text="Link to publisher universes"
    )
    titles = serializers.HyperlinkedIdentityField(
        view_name='publisher-titles',
        help_text="Link to publisher titles"
    )

    class Meta:
        model = models.Publisher
        fields = ("id", "name", "universes", "titles")
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            'name': {'help_text': "Publisher name"},
        }


# Universe


class UniverseListSerializer(ListSerializer):
    class Meta(ListSerializer.Meta):
        model = models.Universe


class UniverseDetailSerializer(serializers.HyperlinkedModelSerializer):
    titles = serializers.HyperlinkedIdentityField(
        view_name='universe-titles',
        help_text="Link to universe titles"
    )

    class Meta:
        model = models.Universe
        fields = ("id", "name", "desc", "publisher", "titles")
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            'name': {'help_text': "Universe name"},
            'desc': {'help_text': "Universe description"},
            'publisher': {'help_text': "Link to publisher"}
        }


# Title


class TitleListSerializer(ListSerializer):
    class Meta(ListSerializer.Meta):
        model = models.Title


class TitleDetailSerializer(serializers.HyperlinkedModelSerializer):
    publisher_name = serializers.CharField(
        source="publisher.name",
        help_text="Publisher name"
    )
    universe_name = serializers.CharField(
        source="universe.name",
        help_text="Universe name"
    )
    title_type = serializers.CharField(
        source="title_type.name",
        help_text="Title type"
    )
    issues = serializers.HyperlinkedIdentityField(
        view_name='title-issues',
        help_text="Link to title issues"
    )

    class Meta:
        model = models.Title
        fields = ("id", "publisher_name", "universe_name", "name", "title_type", "publisher", "universe", "issues")
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            'name': {'help_text': "Title name"},
            'publisher': {'help_text': "Link to publisher"},
            'universe': {'help_text': "Link to universe"}
        }


# Issue


class IssueListSerializer(ListSerializer):
    class Meta(ListSerializer.Meta):
        model = models.Issue


class IssueDetailSerializer(serializers.HyperlinkedModelSerializer):
    publisher_name = serializers.CharField(
        source="title.publisher.name",
        help_text="Publisher name"
    )
    universe_name = serializers.CharField(
        source="title.universe.name",
        help_text="Universe name"
    )
    title_name = serializers.CharField(
        source="title.name",
        help_text="Title name"
    )
    title_type = serializers.CharField(
        source="title.title_type.name",
        help_text="Title type"
    )
    publisher = serializers.HyperlinkedRelatedField(
        source="title.publisher",
        view_name="publisher-detail",
        help_text="Link to publisher",
        read_only=True)
    universe = serializers.HyperlinkedRelatedField(
        source="universe.publisher",
        view_name="universe-detail",
        help_text="Link to universe",
        read_only=True)

    class Meta:
        model = models.Issue
        fields = ("id", "publisher_name", "universe_name", "title_name", "title_type", "name", "number", "desc",
                  "publish_date", "download_link", "publisher", "universe", "title")
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            'name': {'help_text': "Issue name"},
            'number': {'help_text': "Issue number"},
            'desc': {'help_text': "Issue description"},
            'publish_date': {'help_text': "Issue publish date"},
            'download_link': {'help_text': "Download link"},
            'title': {'help_text': "Link to title"},
        }


# ParserRun


class ParserRunListSerializer(serializers.HyperlinkedModelSerializer):
    parser_code = serializers.CharField(
        source="parser",
        help_text="Parser code",
        read_only=True
    )
    status_code = serializers.CharField(
        source="status",
        help_text="Status code",
        read_only=True
    )
    class Meta:
        model = models.ParserRun
        fields = ("id", settings.REST_FRAMEWORK['URL_FIELD_NAME'], "parser_code", "parser_name", "status_code",
                  "status_name", "start", "end", "error", "page")
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            settings.REST_FRAMEWORK["URL_FIELD_NAME"]: {'help_text': "Link to detail API endpoint"},
            'parser_name': {'help_text': "Parser display name"},
            'status_name': {'help_text': "Status display name"},
            'start': {'help_text': "Parser run start date and time"},
            'end': {'help_text': "Parser run end date and time"},
            'error': {'help_text': "Error message"}
        }


class ParserRunDetailSerializer(serializers.HyperlinkedModelSerializer):
    parser = serializers.CharField(
        help_text="Parser code",
        read_only=True
    )
    status = serializers.CharField(
        help_text="Status code",
        read_only=True
    )
    run_details_url = serializers.HyperlinkedIdentityField(
        view_name="parserrun-details",
        help_text="Link to parser run's detail list",
        read_only=True
    )

    class Meta:
        model = models.ParserRun
        fields = ("id", "parser", "parser_name", "status",
                  "status_name", "start", "end", "items_count", "processed", "error", "error_detail", "run_details_url")
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            'parser_name': {'help_text': "Parser display name"},
            'status_name': {'help_text': "Status display name"},
            'start': {'help_text': "Parser run start date and time"},
            'end': {'help_text': "Parser run end date and time"},
            'items_count': {'help_text': "Count of items to be processed"},
            'processed': {'help_text': "Count of processed items"},
            'error': {'help_text': "Error message"},
            'error_detail': {'help_text': "Error detail"}
        }


# ParserRunDetails


class CloudFilesParserRunDetailListSerializer(serializers.HyperlinkedModelSerializer):
    step_name=serializers.CharField(source="file_key")

    class Meta:
        model = models.CloudFilesParserRunDetail
        fields = ("id", settings.REST_FRAMEWORK['URL_FIELD_NAME'], "status", "status_name", "start", "end", "error",
                  "created", "step_name")
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            settings.REST_FRAMEWORK['URL_FIELD_NAME']: {'help_text': "Link to detail API endpoint"},
            'status': {'help_text': "Status code"},
            'status_name': {'help_text': "Status display name"},
            'start': {'help_text': "Parser step start date and time"},
            'end': {'help_text': "Parser step end date and time"},
            'error': {'help_text': "Error message"},
            'created': {'help_text': "Was issue created as result of parser run"}
        }


class CloudFilesParserRunDetailDetailSerializer(serializers.HyperlinkedModelSerializer):
    issue_name = serializers.CharField(
        read_only=True,
        help_text="Name of issue matching file key "
    )

    class Meta:
        model = models.CloudFilesParserRunDetail
        fields = ("id", settings.REST_FRAMEWORK['URL_FIELD_NAME'], "status", "status_name", "start", "end", "file_key",
                  "regex", "groups", "issue", "created", "error", "error_detail", "issue_name")
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            settings.REST_FRAMEWORK['URL_FIELD_NAME']: {'help_text': "Link to detail API endpoint"},
            'status': {'help_text': "Status code"},
            'status_name': {'help_text': "Status display name"},
            'start': {'help_text': "Parser step start date and time"},
            'end': {'help_text': "Parser step end date and time"},
            'file_key': {'help_text': "File key in DO cloud"},
            'regex': {'help_text': "Regex, used for parse"},
            'groups': {'help_text': "Parsed groups"},
            'issue': {'help_text': "Issue matching file key"},
            'error': {'help_text': "Error message"},
            'error_detail': {'help_text': "Error detail"},
            'created': {'help_text': "Was issue created as result of parser run"}
        }


# App Token


class AppTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AppToken
        fields = ("id", "app_name", "description", "token")
        read_only_fields = ("token", "id", "app_name")
        extra_kwargs = {
            'id': {'help_text': "Unique identifier"},
            'app_name': {'help_text': "App name. Unique for user"},
            'description': {'help_text': "App description"},
            'token': {'help_text': "Token"},
        }
