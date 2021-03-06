from django.db.models import Count
from django_filters import rest_framework as filters
from django_filters.widgets import BooleanWidget

from comics_db import models

TITLE_CHOICES = tuple((x.name, x.name) for x in models.TitleType.objects.all())
PARSER_CHOICES = models.ParserRun.PARSER_CHOICES
RUN_STATUS_CHOICES = models.ParserRun.STATUS_CHOICES
RUN_DETAIL_STATUS_CHOICES = models.ParserRunDetail.STATUS_CHOICES
ACTION_CHOICES = models.MarvelAPIParserRunDetail.ACTION_CHOICES
ENTITY_TYPE_CHOICES = models.MarvelAPIParserRunDetail.ENTITY_TYPE_CHOICES
MARVEL_API_SERIES_TYPE_CHOICES = tuple((x['series_type'], x['series_type'])
                                       for x in models.MarvelAPISeries.objects.values("series_type").distinct())


class PublisherFilter(filters.FilterSet):
    name = filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
        label="Name",
        help_text="`name` contains (ignore case)"
    )


class UniverseFilter(filters.FilterSet):
    name = filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
        label="Name",
        help_text="`name` contains (ignore case)"
    )
    publisher_id = filters.NumberFilter(
        field_name="publisher_id",
        label="Publisher ID",
        help_text="`publisher_id` equals"
    )
    publisher_name = filters.CharFilter(
        field_name="publisher__name",
        lookup_expr="icontains",
        label="Publisher Name",
        help_text="`publisher.name` contains (ignore case)"
    )


class TitleFilter(filters.FilterSet):
    name = filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
        label="Name",
        help_text="`name` contains (ignore case)"
    )
    title_type = filters.ChoiceFilter(
        field_name="title_type__name",
        lookup_expr="iexact",
        label="Title type",
        help_text="`title_type` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format("\n".join(map(lambda x: "* %s" % x[0], TITLE_CHOICES))),
        choices=TITLE_CHOICES
    )
    publisher_id = filters.NumberFilter(
        field_name="publisher_id",
        label="Publisher ID",
        help_text="`publisher_id` equals"
    )
    publisher_name = filters.CharFilter(
        field_name="publisher__name",
        lookup_expr="icontains",
        label="Publisher Name",
        help_text="`publisher.name` contains (ignore case)"
    )
    universe_id = filters.NumberFilter(
        field_name="universe_id",
        label="Universe ID",
        help_text="`universe_id` equals"
    )
    universe_name = filters.CharFilter(
        field_name="universe__name",
        lookup_expr="icontains",
        label="Universe Name",
        help_text="`universe.name` contains (ignore case)"
    )


class IssueFilter(filters.FilterSet):
    name = filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
        label="Name",
        help_text="`name` contains (ignore case)"
    )
    title_type = filters.ChoiceFilter(
        field_name="title__title_type__name",
        lookup_expr="iexact",
        label="Title type",
        help_text="`title_type` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format("\n".join(map(lambda x: "* %s" % x[0], TITLE_CHOICES))),
        choices=TITLE_CHOICES
    )
    publisher_id = filters.NumberFilter(
        field_name="title__publisher_id",
        label="Publisher ID",
        help_text="`publisher_id` equals"
    )
    publisher_name = filters.CharFilter(
        field_name="title__publisher__name",
        lookup_expr="icontains",
        label="Publisher Name",
        help_text="`publisher.name` contains (ignore case)"
    )
    universe_id = filters.NumberFilter(
        field_name="title__universe_id",
        label="Universe ID",
        help_text="`universe_id` equals"
    )
    universe_name = filters.CharFilter(
        field_name="title__universe__name",
        lookup_expr="icontains",
        label="Universe Name",
        help_text="`universe.name` contains (ignore case)"
    )
    publish_year = filters.NumberFilter(
        field_name="publish_date",
        lookup_expr="year",
        label="Publish Year",
        help_text="Publish year equals"
    )
    publish_date_gte = filters.DateFilter(
        field_name="publish_date",
        lookup_expr="gte",
        label="Publish Date after",
        help_text="`publish_date` greater than or equal. Date format: YYYY-MM-DD"
    )
    publish_date_lte = filters.DateFilter(
        field_name="publish_date",
        lookup_expr="lte",
        label="Publish Date before",
        help_text="`publish_date` less than or equal. Date format: YYYY-MM-DD"
    )


class ParserRunFilter(filters.FilterSet):
    parser = filters.ChoiceFilter(
        field_name="parser",
        lookup_expr="iexact",
        choices=PARSER_CHOICES,
        label="Parser",
        help_text="`parser` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format("\n".join(map(lambda x: "* `%s` - %s" % x, PARSER_CHOICES)))

    )
    start_date = filters.CharFilter(
        field_name="start__date",
        label="Start date",
        help_text="`start` date equals. Date format: YYYY-MM-DD  (iso-8601 date)"
    )
    end_date = filters.CharFilter(
        field_name="end__date",
        label="End date",
        help_text="`end` date equals. Date format: YYYY-MM-DD  (iso-8601 date)"
    )
    start_lte = filters.DateTimeFilter(
        field_name="start",
        lookup_expr="lte",
        label="Start",
        help_text="`start` less than or equal. Date format: YYYY-MM-DDThh:mm:ss.sTZD (iso-8601 datetime)"
    )
    start_gte = filters.DateTimeFilter(
        field_name="start",
        lookup_expr="gte",
        label="Start",
        help_text="`start` greater than or equal. Date format: YYYY-MM-DDThh:mm:ss.sTZD (iso-8601 datetime)"
    )
    end_lte = filters.DateTimeFilter(
        field_name="end",
        lookup_expr="lte",
        label="End",
        help_text="`end` less than or equal. Date format: YYYY-MM-DDThh:mm:ss.sTZD (iso-8601 datetime)"
    )
    end_gte = filters.DateTimeFilter(
        field_name="end",
        lookup_expr="gte",
        label="End",
        help_text="`end` greater than or equal. Date format: YYYY-MM-DDThh:mm:ss.sTZD (iso-8601 datetime)"
    )
    status = filters.ChoiceFilter(
        field_name="status",
        lookup_expr="iexact",
        choices=RUN_STATUS_CHOICES,
        label="Status",
        help_text="`status` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format("\n".join(map(lambda x: "* `%s` - %s" % x, RUN_STATUS_CHOICES)))

    )
    error = filters.CharFilter(
        field_name="error",
        lookup_expr="icontains",
        label="Error",
        help_text="`error` contains (ignore case)"
    )


class ParserRunDetailFilter(filters.FilterSet):
    start_lte = filters.DateTimeFilter(
        field_name="start",
        lookup_expr="lte",
        label="Start",
        help_text="`start` less than or equal. Date format: YYYY-MM-DDThh:mm:ss.sTZD (iso-8601 datetime)"
    )
    start_gte = filters.DateTimeFilter(
        field_name="start",
        lookup_expr="gte",
        label="Start",
        help_text="`start` greater than or equal. Date format: YYYY-MM-DDThh:mm:ss.sTZD (iso-8601 datetime)"
    )
    end_lte = filters.DateTimeFilter(
        field_name="end",
        lookup_expr="lte",
        label="End",
        help_text="`end` less than or equal. Date format: YYYY-MM-DDThh:mm:ss.sTZD (iso-8601 datetime)"
    )
    end_gte = filters.DateTimeFilter(
        field_name="end",
        lookup_expr="gte",
        label="End",
        help_text="`end` greater than or equal. Date format: YYYY-MM-DDThh:mm:ss.sTZD (iso-8601 datetime)"
    )
    status = filters.ChoiceFilter(
        field_name="status",
        lookup_expr="iexact",
        choices=RUN_DETAIL_STATUS_CHOICES,
        label="Status",
        help_text="`status` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format("\n".join(map(lambda x: "* `%s` - "
                                                                              "%s" % x, RUN_DETAIL_STATUS_CHOICES)))

    )
    error = filters.CharFilter(
        field_name="error",
        lookup_expr="icontains",
        label="Error",
        help_text="`error` contains (ignore case)"
    )


class CloudFilesParserRunDetailFilter(ParserRunDetailFilter):
    file_key = filters.CharFilter(
        field_name="file_key",
        lookup_expr="icontains",
        label="File key",
        help_text="`file_key` contains (ignore case)"
    )
    created = filters.BooleanFilter(
        field_name="created",
        label="Created",
        help_text="`created` equals",
        widget=BooleanWidget()
    )


class MarvelAPIParserRunDetailFilter(ParserRunDetailFilter):
    action = filters.ChoiceFilter(
        field_name="action",
        lookup_expr="iexact",
        choices=ACTION_CHOICES,
        label="Action",
        help_text="`parser` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format("\n".join(map(lambda x: "* `%s` - %s" % x, ACTION_CHOICES)))

    )
    entity_type = filters.ChoiceFilter(
        field_name="entity_type",
        lookup_expr="iexact",
        choices=ENTITY_TYPE_CHOICES,
        label="Entity_type",
        help_text="`parser` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format("\n".join(map(lambda x: "* `%s` - %s" % x, ENTITY_TYPE_CHOICES)))

    )
    entity_id = filters.NumberFilter(
        field_name="entity_id",
        label="Entity_id",
        help_text="`entity_id` equals"
    )
    created = filters.BooleanFilter(
        field_name="created",
        label="Created",
        help_text="`created` equals",
        widget=BooleanWidget()
    )


class MarvelAPICreatorMergeRunDetailFilter(ParserRunDetailFilter):
    created = filters.BooleanFilter(
        field_name="created",
        label="Created",
        help_text="`created` equals",
        widget=BooleanWidget()
    )
    db_name = filters.CharFilter(
        field_name="db_creator__name",
        lookup_expr="icontains",
        label="DB creator",
        help_text="`db creator` contains (ignore case)"
    )
    api_name = filters.CharFilter(
        field_name="api_creator__full_name",
        lookup_expr="icontains",
        label="API creator",
        help_text="`API creator` contains (ignore case)"
    )


class MarvelAPICharacterMergeRunDetailFilter(ParserRunDetailFilter):
    created = filters.BooleanFilter(
        field_name="created",
        label="Created",
        help_text="`created` equals",
        widget=BooleanWidget()
    )
    db_name = filters.CharFilter(
        field_name="db_character__name",
        lookup_expr="icontains",
        label="DB creator",
        help_text="`db creator` contains (ignore case)"
    )
    api_name = filters.CharFilter(
        field_name="api_character__name",
        lookup_expr="icontains",
        label="API creator",
        help_text="`API creator` contains (ignore case)"
    )


class MarvelAPIEventMergeRunDetailFilter(ParserRunDetailFilter):
    created = filters.BooleanFilter(
        field_name="created",
        label="Created",
        help_text="`created` equals",
        widget=BooleanWidget()
    )
    db_name = filters.CharFilter(
        field_name="db_event__name",
        lookup_expr="icontains",
        label="DB creator",
        help_text="`db creator` contains (ignore case)"
    )
    api_name = filters.CharFilter(
        field_name="api_event__title",
        lookup_expr="icontains",
        label="API creator",
        help_text="`API creator` contains (ignore case)"
    )


class MarvelAPITitleMergeRunDetailFilter(ParserRunDetailFilter):
    api_name = filters.CharFilter(
        field_name="api_title__title",
        lookup_expr="icontains",
    )
    db_name = filters.CharFilter(
        field_name="db_title__name",
        lookup_expr="icontains",
    )
    merge_result = filters.ChoiceFilter(
        field_name="merge_result",
        lookup_expr="iexact",
        choices=models.MarvelAPITitleMergeParserRunDetail.RESULT_CHOICES,
        label="Merge_result",
        help_text="`parser` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format(
            "\n".join(map(lambda x: "* `%s` - %s" % x, models.MarvelAPITitleMergeParserRunDetail.RESULT_CHOICES)))

    )


class MarvelAPIIssueMergeRunDetailFilter(ParserRunDetailFilter):
    api_name = filters.CharFilter(
        field_name="api_comic__title",
        lookup_expr="icontains",
    )
    db_name = filters.CharFilter(
        field_name="db_issue__name",
        lookup_expr="icontains",
    )
    merge_result = filters.ChoiceFilter(
        field_name="merge_result",
        lookup_expr="iexact",
        choices=models.MarvelAPIIssueMergeParserRunDetail.RESULT_CHOICES,
        label="Merge_result",
        help_text="`parser` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format(
            "\n".join(map(lambda x: "* `%s` - %s" % x, models.MarvelAPIIssueMergeParserRunDetail.RESULT_CHOICES)))

    )


class AppTokenFilter(filters.FilterSet):
    app_name = filters.CharFilter(
        field_name="app_name",
        lookup_expr="icontains",
        label="App name",
        help_text="`app_name` contains (ignore case)"
    )


class MarvelAPISeriesFilter(filters.FilterSet):
    id = filters.NumberFilter(
        field_name="id",
        label="Id",
        help_text="`id` equals"
    )
    title = filters.CharFilter(
        field_name="title",
        lookup_expr="icontains",
        label="Title",
        help_text="`title` contains (ignore case)"
    )
    start_year = filters.NumberFilter(
        field_name="start_year",
        label="Start_year",
        help_text="`start_year` equals"
    )
    end_year = filters.NumberFilter(
        field_name="end_year",
        label="End_year",
        help_text="`end_year` equals"
    )
    rating = filters.CharFilter(
        field_name="rating",
        lookup_expr="icontains",
        label="Rating",
        help_text="`rating` contains (ignore case)"
    )
    series_type = filters.ChoiceFilter(
        field_name="series_type",
        lookup_expr="iexact",
        choices=MARVEL_API_SERIES_TYPE_CHOICES,
        label="Series_type",
        help_text="`series_type` equals (ignore_case).\n"
                  "Possible choices are:\n{0}".format(
            "\n".join(map(lambda x: "* `%s` - %s" % x, MARVEL_API_SERIES_TYPE_CHOICES)))
    )
    show_ignored = filters.BooleanFilter(method="show_ignored_filter")
    show_matched = filters.BooleanFilter(method="show_matched_filter")

    def show_ignored_filter(self, queryset, name, value):
        if not value:
            queryset = queryset.exclude(ignore=True)
        return queryset

    def show_matched_filter(self, queryset, name, value):
        if not value:
            queryset = queryset.annotate(db_titles_count=Count("db_titles")).exclude(db_titles_count__gt=0)
        return queryset


class MarvelAPIComicsFilter(filters.FilterSet):
    id = filters.NumberFilter(
        field_name="id",
        label="Id",
        help_text="`id` equals"
    )
    title = filters.CharFilter(
        field_name="title",
        lookup_expr="icontains",
        label="Title",
        help_text="`title` contains (ignore case)"
    )
    issue_number = filters.NumberFilter(
        field_name="issue_number",
        label="Issue number",
        help_text="`issue_number` equals"
    )
    page_count = filters.NumberFilter(
        field_name="page_count",
        label="page_count",
        help_text="`page_count` equals"
    )
    description = filters.CharFilter(
        field_name="description",
        label="description",
        help_text="`description` contains (ignore case)"
    )
    series_id = filters.NumberFilter(
        field_name="series_id"
    )

    show_matched = filters.BooleanFilter(method="show_matched_filter")

    def show_matched_filter(self, queryset, name, value):
        if not value:
            queryset = queryset.annotate(db_issues_count=Count("db_issues")).exclude(db_issues_count__gt=0)
        return queryset