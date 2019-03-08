from django_filters import rest_framework as filters
from django_filters.widgets import BooleanWidget

from comics_db import models

TITLE_CHOICES = tuple((x.name, x.name) for x in models.TitleType.objects.all())
PARSER_CHOICES = models.ParserRun.PARSER_CHOICES
RUN_STATUS_CHOICES = models.ParserRun.STATUS_CHOICES
RUN_DETAIL_STATUS_CHOICES = models.ParserRunDetail.STATUS_CHOICES


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


class CloudFilesParserRunDetailFilter(filters.FilterSet):
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
        field_name="get_status_display",
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
    created = filters.BooleanFilter(
        field_name="created",
        label="Created",
        help_text="`created` equals",
        widget=BooleanWidget()
    )


class AppTokenFilter(filters.FilterSet):
    app_name = filters.CharFilter(
        field_name="app_name",
        lookup_expr="icontains",
        label="App name",
        help_text="`app_name` contains (ignore case)"
    )