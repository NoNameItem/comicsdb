import tempfile

import requests
from django.db import models
from django.db.models.aggregates import Sum
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django.contrib.auth.models import User
from django.utils.text import slugify
from knox.models import AuthToken

from comicsdb import settings
from comics_db.fields import ThumbnailImageField


# Create your models here.


def unique_slugify(klass, value, counter = 0, allow_unicode=True):
    if counter:
        slug = slugify("{0}-{1}".format(value, counter), allow_unicode)
    else:
        slug = slugify(value, allow_unicode)

    if klass.objects.filter(slug=slug).exists():
        return unique_slugify(klass, value, counter + 1, allow_unicode)
    else:
        return slug


########################################################################################################################
# Parsers
########################################################################################################################

class ParserRun(models.Model):
    PARSER_CHOICES = (
        ("BASE", "Base parser"),
        ("CLOUD_FILES", "Cloud files parser"),
        ("MARVEL_API", "Marvel API parser"),
        ("MARVEL_API_CREATOR_MERGE", "Marvel API creator merge"),
        ("MARVEL_API_CHARACTER_MERGE", "Marvel API character merge"),
        ("MARVEL_API_EVENT_MERGE", "Marvel API event merge"),
        ("MARVEL_API_TITLE_MERGE", "Marvel API title merge"),
        ("MARVEL_API_ISSUE_MERGE", "Marvel API comics merge"),
    )

    STATUS_CHOICES = (
        ("COLLECTING", "Collecting data"),
        ("RUNNING", "Running"),
        ("SUCCESS", "Successfully ended"),
        ("ENDED_WITH_ERRORS", "Ended with errors"),
        ("API_THROTTLE", "API rate limit has been surpassed."),
        ("CRITICAL_ERROR", "Critical Error"),
        ("INVALID_PARSER", "Invalid parser implementation"),
        ("QUEUE", "In queue")
    )

    parser = models.CharField(max_length=30, choices=PARSER_CHOICES, default=PARSER_CHOICES[0][0])
    start = models.DateTimeField(default=timezone.now)
    end = models.DateTimeField(null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    items_count = models.IntegerField(null=True)
    error = models.TextField(blank=True)
    error_detail = models.TextField(blank=True)
    celery_task_id = models.CharField(max_length=100, null=True)

    @property
    def parser_name(self):
        return self.get_parser_display()

    @property
    def status_name(self):
        return self.get_status_display()

    @property
    def run_details_url(self):
        if self.parser == 'CLOUD_FILES':
            return reverse('parserrun-details-cloud', args=(self.id,))
        elif self.parser == 'MARVEL_API':
            return reverse('parserrun-details-marvel-api', args=(self.id,))
        elif self.parser == 'MARVEL_API_CREATOR_MERGE':
            return reverse('parserrun-details-marvel-api-creator-merge', args=(self.id,))
        elif self.parser == 'MARVEL_API_CHARACTER_MERGE':
            return reverse('parserrun-details-marvel-api-character-merge', args=(self.id,))
        elif self.parser == 'MARVEL_API_EVENT_MERGE':
            return reverse('parserrun-details-marvel-api-event-merge', args=(self.id,))
        elif self.parser == 'MARVEL_API_TITLE_MERGE':
            return reverse('parserrun-details-marvel-api-title-merge', args=(self.id,))
        elif self.parser == 'MARVEL_API_ISSUE_MERGE':
            return reverse('parserrun-details-marvel-api-issue-merge', args=(self.id,))
        return None

    @property
    def page(self):
        return reverse('parser-log-detail', args=(self.id,))

    @property
    def details(self):
        if self.parser == 'CLOUD_FILES':
            return self.cloudfilesparserrundetails
        elif self.parser == 'MARVEL_API':
            return self.marvelapiparserrundetails
        elif self.parser == 'MARVEL_API_CREATOR_MERGE':
            return self.marvelapicreatormergeparserrundetails
        elif self.parser == 'MARVEL_API_CHARACTER_MERGE':
            return self.marvelapicharactermergeparserrundetails
        elif self.parser == 'MARVEL_API_EVENT_MERGE':
            return self.marvelapieventmergeparserrundetails
        elif self.parser == 'MARVEL_API_TITLE_MERGE':
            return self.marvelapititlemergeparserrundetails
        elif self.parser == 'MARVEL_API_ISSUE_MERGE':
            return self.marvelapiissuemergeparserrundetails
        else:
            return None

    @property
    def success_count(self):
        if self.details is not None:
            if self.parser == 'MARVEL_API':
                if self.status == 'COLLECTING':
                    return self.details.filter(status='SUCCESS').count()
                else:
                    return self.details.filter(status='SUCCESS', action='PROCESS').count()
            else:
                return self.details.filter(status='SUCCESS').count()
        else:
            return 0

    @property
    def error_count(self):
        if self.details is not None:
            if self.parser == 'MARVEL_API':
                if self.status == 'COLLECTING':
                    return self.details.filter(status='ERROR').count()
                else:
                    return self.details.filter(status='ERROR', action='PROCESS').count()
            else:
                return self.details.filter(status='ERROR').count()
        else:
            return 0

    @property
    def processed(self):
        if self.details is not None:
            if self.parser == 'MARVEL_API':
                if self.status == 'COLLECTING':
                    return self.details.exclude(status='RUNNING').count()
                else:
                    return self.details.exclude(status='RUNNING').filter(action='PROCESS').count()
            else:
                return self.details.exclude(status='RUNNING').count()
        else:
            return 0

    class Meta:
        ordering = ["-start"]


class ParserRunParams(models.Model):
    parser_run = models.ForeignKey(ParserRun, on_delete=models.CASCADE, related_name="parameters")
    name = models.CharField(max_length=100)
    val = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]


class ParserRunDetail(models.Model):
    STATUS_CHOICES = (
        ("RUNNING", "Running"),
        ("SUCCESS", "Success"),
        ("ERROR", "Error")
    )

    parser_run = models.ForeignKey(ParserRun, on_delete=models.CASCADE, related_name='%(class)ss')
    start = models.DateTimeField(default=timezone.now)
    end = models.DateTimeField(null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    error = models.TextField(blank=True)
    error_detail = models.TextField(blank=True)

    def end_with_error(self, error, error_detail=""):
        self.status = "ERROR"
        self.end = timezone.now()
        self.error = error
        self.error_detail = error_detail
        self.save()

    def end_with_success(self):
        self.status = "SUCCESS"
        self.end = timezone.now()
        self.save()

    @property
    def status_name(self):
        return self.get_status_display()

    class Meta:
        abstract = True
        ordering = ["parser_run", "-start"]


class CloudFilesParserRunDetail(ParserRunDetail):
    file_key = models.TextField()
    regex = models.TextField()
    groups = models.TextField(blank=True)
    issue = models.ForeignKey("Issue", null=True, on_delete=models.SET_NULL)
    created = models.BooleanField(default=False)

    def issue_name(self):
        if self.issue:
            return self.issue.name
        else:
            return None


class MarvelAPIParserRunDetail(ParserRunDetail):
    ENTITY_TYPE_CHOICES = (
        ("COMICS", "Comics"),
        ("CHARACTER", "Character"),
        ("CREATOR", "Creator"),
        ("EVENT", "Event"),
        ("SERIES", "Series")
    )
    ACTION_CHOICES = (
        ('GET', 'Getting data from API'),
        ('PROCESS', 'Processing data'),
    )

    entity_type = models.CharField(max_length=10, choices=ENTITY_TYPE_CHOICES)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    entity_id = models.IntegerField(null=True)
    data = models.TextField(blank=True)

    @property
    def action_name(self):
        return self.get_action_display()

    @property
    def entity_type_name(self):
        return self.get_entity_type_display()

    @property
    def step_name(self):
        if self.action == "PROCESS":
            return "{0} #{1}".format(self.get_entity_type_display(), self.entity_id)
        else:
            return "Getting {0}".format(self.get_entity_type_display())


class MarvelAPICreatorMergeParserRunDetail(ParserRunDetail):
    api_creator = models.ForeignKey('MarvelAPICreator', on_delete=models.CASCADE)
    db_creator = models.ForeignKey('Creator', on_delete=models.CASCADE, null=True)
    created = models.BooleanField(default=False)


class MarvelAPICharacterMergeParserRunDetail(ParserRunDetail):
    api_character = models.ForeignKey('MarvelAPICharacter', on_delete=models.CASCADE)
    db_character = models.ForeignKey('Character', on_delete=models.CASCADE, null=True)
    created = models.BooleanField(default=False)


class MarvelAPIEventMergeParserRunDetail(ParserRunDetail):
    api_event = models.ForeignKey('MarvelAPIEvent', on_delete=models.CASCADE)
    db_event = models.ForeignKey('Event', on_delete=models.CASCADE, null=True)
    created = models.BooleanField(default=False)


class MarvelAPITitleMergeParserRunDetail(ParserRunDetail):
    RESULT_CHOICES = (
        ('ALREADY', 'Already matched'),
        ('SUCCESS', 'Success'),
        ('NOT_FOUND', 'Match not found'),
        ('DUPLICATES', 'Multiple matches'),
        ('MANUAL', 'Manually changed')
    )
    api_title = models.ForeignKey('MarvelAPISeries', on_delete=models.CASCADE, null=True)
    db_title = models.ForeignKey('Title', on_delete=models.CASCADE, null=True)
    merge_result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True)

    def merge_result_name(self):
        return self.get_merge_result_display()

    def possible_matches(self):
        if self.merge_result == 'DUPLICATES':
            return render_to_string("comics_db/admin/possible_api_titles.html",
                          {'titles': self.db_title.possible_matches.all(), 'db_title_id': self.db_title.id})
        return None

    @property
    def db_name(self):
        return str(self.db_title)


class MarvelAPIIssueMergeParserRunDetail(ParserRunDetail):
    RESULT_CHOICES = (
        ('ALREADY', 'Already matched'),
        ('SUCCESS', 'Success'),
        ('NOT_FOUND', 'Match not found'),
        ('DUPLICATES', 'Multiple matches'),
        ('MANUAL', 'Manually changed')
    )
    api_comic = models.ForeignKey('MarvelAPIComics', on_delete=models.CASCADE, null=True)
    db_issue = models.ForeignKey('Issue', on_delete=models.CASCADE, null=True)
    merge_result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True)

    def merge_result_name(self):
        return self.get_merge_result_display()

    def possible_matches(self):
        if self.merge_result == 'DUPLICATES':
            return render_to_string("comics_db/admin/possible_api_issues.html",
                          {'comics': self.db_issue.possible_matches.all(), 'db_issue_id': self.db_issue.id})
        return None

    @property
    def db_name(self):
        return str(self.db_issue)

    @property
    def api_series_link(self):
        return reverse('site-marvel-api-series-detail', args=(self.db_issue.title.api_series.id,))

########################################################################################################################
# Comics Info
########################################################################################################################


MARVEL_API_STATUS_CHOICES = (
    ('NEW', 'New'),
    ('NO_ID', 'Can\'t find ID'),
    ('ID_GET_DATA', 'ID found, need to get data'),
    ('PROCESSED', 'Processed')
)


def get_publisher_poster_name(instance, filename):
    return "publisher_poster/{0}_poster.{1}".format(instance.name, filename.split('.')[-1])


def get_publisher_logo_name(instance, filename):
    return "publisher_logo/{0}_logo.{1}".format(instance.name, filename.split('.')[-1])


class Publisher(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = ThumbnailImageField(null=True, upload_to=get_publisher_logo_name, thumb_width=100)
    poster = ThumbnailImageField(null=True, upload_to=get_publisher_poster_name, thumb_width=520)
    desc = models.TextField(blank=True)
    slug = models.SlugField(max_length=500, unique=True, allow_unicode=True)

    # Dates
    created_dt = models.DateTimeField(auto_now_add=True)
    modified_dt = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.slug = self.get_slug()
        super(Publisher, self).save(*args, **kwargs)

    def get_slug(self):
        return slugify(self.name, allow_unicode=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("site-publisher-detail", args=(self.slug,))

    @property
    def issue_count(self):
        return self.titles.aggregate(models.Count('issues'))['issues__count']

    class Meta:
        ordering = ["name"]


def get_creator_photo_name(instance, filename):
    return "creator/{0}_photo.{1}".format(instance.name, filename.split('.')[-1])


def get_creator_image_name(instance, filename):
    return "creator/{0}_image.{1}".format(instance.name, filename.split('.')[-1])


class Creator(models.Model):
    name = models.CharField(max_length=500)
    bio = models.TextField(blank=True)
    photo = ThumbnailImageField(null=True, upload_to=get_creator_photo_name, thumb_width=100)
    image = ThumbnailImageField(null=True, upload_to=get_creator_image_name, thumb_width=520)
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)
    url = models.TextField(blank=True)

    # Dates
    created_dt = models.DateTimeField(auto_now_add=True)
    modified_dt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_slug(self):
        return unique_slugify(self.__class__, self.name)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Creator, self).save(force_insert, force_update, using, update_fields)

    def fill_from_marvel_api(self, api_creator: 'MarvelAPICreator' = None):
        api_creator = api_creator or self.marvel_api_creator

        # Name
        self.name = api_creator.full_name

        # Marvel URL
        try:
            self.url = api_creator.urls.get(type="detail").url
        except MarvelAPISiteUrl.DoesNotExist:
            self.url = ''

        # Image
        try:
            api_image = api_creator.image
            link = "{0.path}.{0.extension}".format(api_image)
            r = requests.get(link, allow_redirects=True)
            with tempfile.NamedTemporaryFile() as image:
                image.write(r.content)
                self.image.save(link, image)

        except MarvelAPIImage.DoesNotExist:
            image = None

    class Meta:
        ordering = ("name",)


def get_universe_poster_name(instance, filename):
    return "universe_poster/{0}_poster.{1}".format(instance.name, filename.split('.')[-1])


class Universe(models.Model):
    name = models.CharField(max_length=100)
    desc = models.TextField(blank=True)
    slug = models.SlugField(max_length=500, unique=True, allow_unicode=True)
    poster = ThumbnailImageField(null=True, upload_to=get_universe_poster_name, thumb_width=520, thumb_height=200)

    publisher = models.ForeignKey(Publisher, on_delete=models.PROTECT, related_name="universes")

    # Dates
    created_dt = models.DateTimeField(auto_now_add=True)
    modified_dt = models.DateTimeField(auto_now=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Universe, self).save(force_insert, force_update, using, update_fields)

    def get_slug(self):
        return unique_slugify(self.__class__, str(self))

    def get_absolute_url(self):
        return reverse("site-universe-detail", args=(self.slug,))

    @property
    def logo(self):
        return self.publisher.logo

    @property
    def issue_count(self):
        return self.titles.aggregate(models.Count('issues'))['issues__count']

    def __str__(self):
        return "[{0.publisher.name}] {0.name}".format(self)

    class Meta:
        unique_together = (("name", "publisher"),)
        ordering = ["publisher", "name"]


class Tag(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name


class TitleType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class TitleCreator(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    title = models.ForeignKey('Title', on_delete=models.CASCADE)
    role = models.CharField(max_length=100)


def get_title_image_name(instance, filename):
    return "title_image/{0}_image.{1}".format(instance.name, filename.split('.')[-1])


class Title(models.Model):
    MARVEL_TITLE_TYPES = {
        'limited': 'Limited',
        'one shot': 'One-shot',
        'ongoing': 'Ongoing',
        'empty': 'Ongoing'
    }

    name = models.CharField(max_length=500)
    path_key = models.CharField(max_length=500)
    desc = models.TextField(blank=True)
    image = ThumbnailImageField(null=True, upload_to=get_title_image_name, thumb_width=380)
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)

    start_year = models.IntegerField(null=True)
    end_year = models.IntegerField(null=True)
    rating = models.TextField(blank=True)

    publisher = models.ForeignKey(Publisher, on_delete=models.PROTECT, related_name="titles")
    universe = models.ForeignKey(Universe, on_delete=models.PROTECT, null=True, related_name="titles", blank=True)
    title_type = models.ForeignKey(TitleType, on_delete=models.PROTECT, related_name="titles")
    creators = models.ManyToManyField(Creator, through=TitleCreator, related_name='titles')

    # Marvel-specific fields
    api_series = models.OneToOneField("MarvelAPISeries", null=True, on_delete=models.SET_NULL, related_name="db_title")
    possible_matches = models.ManyToManyField("MarvelAPISeries", related_name="db_possible_matches")
    marvel_url = models.URLField(max_length=500, blank=True)

    # Dates
    created_dt = models.DateTimeField(auto_now_add=True)
    modified_dt = models.DateTimeField(auto_now=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Title, self).save(force_insert, force_update, using, update_fields)

    def get_slug(self):
        if self.universe:
            name = "[{0.publisher.name}, {0.universe.name}, {0.title_type.name}] {0.path_key}".format(self)
        else:
            name = "[{0.publisher.name}, {0.title_type.name}] {0.path_key}".format(self)
        return unique_slugify(self.__class__, name)

    def __str__(self):
        if self.universe:
            return "[{0.publisher.name}; {0.universe.name}; {0.title_type.name}] {0.name}".format(self)
        else:
            return "[{0.publisher.name}; {0.title_type.name}] {0.name}".format(self)

    @property
    def file_size(self):
        return self.issues.aggregate(file_size=Sum('file_size'))['file_size']

    @property
    def logo(self):
        return self.publisher.logo

    @property
    def site_link(self):
        return reverse('site-title-detail', args=(self.slug,))

    def get_absolute_url(self):
        return self.site_link

    def fill_from_marvel_api(self, api_series=None):
        api_series = api_series or self.api_series

        # Name
        self.name = api_series.title

        # Description
        self.desc = api_series.description or self.desc

        # Start / End Year
        self.start_year = api_series.start_year
        self.end_year = api_series.end_year

        # Rating
        self.rating = api_series.rating or self.rating

        # Title Type
        if api_series.series_type:
            self.title_type = TitleType.objects.get(
                name=self.MARVEL_TITLE_TYPES.get(api_series.series_type, 'Ongoing'))

        # Creators
        title_creators = []
        for api_creator in MarvelAPISeriesCreator.objects.filter(series_fk=api_series):
            title_creator = TitleCreator(title=self, creator=api_creator.creator.creator,
                                                       role=api_creator.role)
            title_creators.append(title_creator)
        TitleCreator.objects.filter(title=self).delete()
        TitleCreator.objects.bulk_create(title_creators)

        # Characters
        title_characters = []
        for api_character in api_series.characters.all():
            title_characters.append(api_character.character)
        self.characters.set(title_characters)

        # Events
        title_events = []
        for api_event in api_series.events.all():
            title_events.append(api_event.event)
        self.events.set(title_events)

        # Marvel URL
        try:
            self.marvel_url = api_series.urls.get(type="detail").url
        except MarvelAPISiteUrl.DoesNotExist:
            self.marvel_url = ''

        # Image
        try:
            api_image = api_series.image
            link = "{0.path}.{0.extension}".format(api_image)
            r = requests.get(link, allow_redirects=True)
            with tempfile.NamedTemporaryFile() as image:
                image.write(r.content)
                self.image.save(link, image)
        except MarvelAPIImage.DoesNotExist:
            pass

    class Meta:
        unique_together = (("name", "publisher", "universe", "title_type"),
                           ("path_key", "publisher", "universe", "title_type"))
        ordering = ["publisher", "universe", "name"]


class IssueCreator(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    issue = models.ForeignKey('Issue', on_delete=models.CASCADE)
    role = models.CharField(max_length=100)


def get_issue_cover_name(instance, filename):
    return "issue_cover/{0}_cover.{1}".format(instance.name, filename.split('.')[-1])


class Issue(models.Model):
    name = models.CharField(max_length=500)
    number = models.FloatField(null=True)
    desc = models.TextField(blank=True)
    publish_date = models.DateField()
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)
    main_cover = ThumbnailImageField(null=True, upload_to=get_issue_cover_name, thumb_width=380)
    link = models.URLField(max_length=1000, unique=True)
    page_count = models.IntegerField(null=True)
    file_size = models.IntegerField(null=True)

    title = models.ForeignKey(Title, on_delete=models.CASCADE, related_name="issues", db_index=True)
    creators = models.ManyToManyField(Creator, through=IssueCreator, related_name='issues')
    tags = models.ManyToManyField(Tag, related_name="issues")

    # Dates
    created_dt = models.DateTimeField(auto_now_add=True)
    modified_dt = models.DateTimeField(auto_now=True)

    # Marvel-specific fields
    marvel_api_comic = models.OneToOneField("MarvelAPIComics", null=True, on_delete=models.SET_NULL,
                                            related_name="db_issue")
    marvel_detail_link = models.URLField(max_length=1000, blank=True)
    marvel_purchase_link = models.URLField(max_length=1000, blank=True)
    possible_matches = models.ManyToManyField("MarvelAPIComics", related_name="db_possible_issues")

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Issue, self).save(force_insert, force_update, using, update_fields)

    def get_slug(self):
        return unique_slugify(self.__class__, self.link.replace('/', '_').replace('.', '_')[8:-4])

    def __str__(self):
        return "[{0.title.publisher.name}, {0.title.universe.name}, {0.publish_date.year}] {0.name}".format(self)

    @property
    def download_link(self):
        return escape_uri_path("{0}/{1.link}".format(settings.DO_PUBLIC_URL, self))

    @property
    def previous_link(self):
        if self.number:
            next_issues = self.title.issues.filter(number__lt=self.number).order_by('-number')
            if next_issues:
                return next_issues[0].site_link
        else:
            return None

    @property
    def next_link(self):
        if self.number:
            next_issues = self.title.issues.filter(number__gt=self.number).order_by('number')
            if next_issues:
                return next_issues[0].site_link
        else:
            return None

    @property
    def site_link(self):
        return reverse('site-issue-detail', args=(self.slug, ))

    def get_absolute_url(self):
        return self.site_link

    @property
    def logo(self):
        return self.title.publisher.logo

    def fill_from_marvel_api(self, api_comic : 'MarvelAPIComics' = None):
        api_comic = api_comic or self.marvel_api_comic

        # Issue number
        self.number = api_comic.issue_number

        # Description
        self.desc = api_comic.description or self.desc

        # Publish Date
        try:
            self.publish_date = api_comic.dates.get(type="onsaleDate").date
        except MarvelAPISiteUrl.DoesNotExist:
            pass

        # Page count
        self.page_count = api_comic.page_count

        # Creators
        issue_creators = []
        for api_creator in MarvelAPIComicsCreator.objects.filter(comics_fk=api_comic):
            issue_creator = IssueCreator(issue=self, creator=api_creator.creator.creator,
                                                       role=api_creator.role)
            issue_creators.append(issue_creator)
        IssueCreator.objects.filter(issue=self).delete()
        IssueCreator.objects.bulk_create(issue_creators)

        # Characters
        issue_characters = []
        for api_character in api_comic.characters.all():
            issue_characters.append(api_character.character)
        self.characters.set(issue_characters)

        # Events
        issue_events = []
        for api_event in api_comic.events.all():
            issue_events.append(api_event.event)
        self.events.set(issue_events)

        # Marvel URLs
        try:
            self.marvel_detail_link = api_comic.urls.get(type="detail").url
        except MarvelAPISiteUrl.DoesNotExist:
            self.marvel_detail_link = ''

        try:
            self.marvel_purchase_link = api_comic.urls.get(type="purchase").url
        except MarvelAPISiteUrl.DoesNotExist:
            self.marvel_purchase_link = ''

        # Image
        try:
            api_image = api_comic.image
            link = "{0.path}.{0.extension}".format(api_image)
            r = requests.get(link, allow_redirects=True)
            with tempfile.NamedTemporaryFile() as image:
                image.write(r.content)
                self.main_cover.save(link, image)
        except MarvelAPIImage.DoesNotExist:
            pass

    class Meta:
        unique_together = (("name", "title", "publish_date"),)
        ordering = ["title", "number"]


def get_character_image_name(instance, filename):
    return "characters/{0}.{1}".format(instance.name, filename.split('.')[-1])


class Character(models.Model):
    name = models.CharField(max_length=500)
    desc = models.TextField(blank=True)
    image = ThumbnailImageField(null=True, upload_to=get_character_image_name, thumb_width=380)
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, related_name="characters")

    titles = models.ManyToManyField(Title, related_name='characters')
    issues = models.ManyToManyField(Issue, related_name='characters')

    # Marvel-specific fields
    marvel_wiki_url = models.TextField(blank=True)

    # Dates
    created_dt = models.DateTimeField(auto_now_add=True)
    modified_dt = models.DateTimeField(auto_now=True)

    def get_slug(self):
        return unique_slugify(self.__class__, str(self))

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Character, self).save(force_insert, force_update, using, update_fields)

    def fill_from_marvel_api(self, api_character: 'MarvelAPICharacter' = None):
        api_character = api_character or self.marvel_api_chararcter

        # Name
        self.name = api_character.name

        # Description
        self.desc = api_character.description or self.desc

        # Marvel URL
        try:
            self.marvel_wiki_url = api_character.urls.get(type="wiki").url
        except MarvelAPISiteUrl.DoesNotExist:
            self.marvel_wiki_url = ''

        # Image
        try:
            api_image = api_character.image
            link = "{0.path}.{0.extension}".format(api_image)
            r = requests.get(link, allow_redirects=True)
            with tempfile.NamedTemporaryFile() as image:
                image.write(r.content)
                self.image.save(link, image)
        except MarvelAPIImage.DoesNotExist:
            self.image = None

    class Meta:
        unique_together = (("publisher", "name"),)


def get_event_image_name(instance, filename):
    return "events/{0}.{1}".format(instance.name, filename.split('.')[-1])


class EventCreator(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    event = models.ForeignKey('Event', on_delete=models.CASCADE)
    role = models.CharField(max_length=50)


class Event(models.Model):
    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True)
    image = models.ImageField(null=True, upload_to='event-image')
    url = models.URLField(max_length=1000, blank=True)
    start = models.DateField(null=True)
    end = models.DateField(null=True)
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)

    publisher = models.ForeignKey(Publisher, null=True, on_delete=models.SET_NULL, related_name="events")

    titles = models.ManyToManyField(Title, related_name='events')
    issues = models.ManyToManyField(Issue, related_name='events')
    characters = models.ManyToManyField(Character, related_name='events')
    creators = models.ManyToManyField(Creator, related_name='events', through=EventCreator)

    # Dates
    created_dt = models.DateTimeField(auto_now_add=True)
    modified_dt = models.DateTimeField(auto_now=True)

    def get_slug(self):
        return unique_slugify(self.__class__, str(self))

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Event, self).save(force_insert, force_update, using, update_fields)

    def fill_from_marvel_api(self, api_event: 'MarvelAPIEvent' = None):
        api_event = api_event or self.marvel_api_event

        # Name
        self.name = api_event.title

        # Description
        self.desc = api_event.description or self.desc

        # Start / End
        self.start = api_event.start
        self.end = api_event.end

        # Creators
        event_creators = []
        for api_creator in MarvelAPIEventCreator.objects.filter(event=api_event):
            event_creator = EventCreator(event=self, creator=api_creator.creator.creator,
                                                       role=api_creator.role)
            event_creators.append(event_creator)

        EventCreator.objects.filter(event=self).delete()
        EventCreator.objects.bulk_create(event_creators)

        # Characters
        event_characters = []
        for api_character in api_event.characters.all():
            event_characters.append(api_character.character)

        self.characters.set(event_characters)

        # Marvel URL
        try:
            self.url = api_event.urls.get(type="wiki").url
        except MarvelAPISiteUrl.DoesNotExist:
            try:
                self.url = api_event.urls.get(type="detail").url
            except MarvelAPISiteUrl.DoesNotExist:
                self.url = ''

        # Image
        try:
            api_image = api_event.image
            link = "{0.path}.{0.extension}".format(api_image)
            r = requests.get(link, allow_redirects=True)
            with tempfile.NamedTemporaryFile() as image:
                image.write(r.content)
                self.image.save(link, image)
        except MarvelAPIImage.DoesNotExist:
            self.image = None

    class Meta:
        unique_together = (("publisher", "name"),)


########################################################################################################################
# Marvel Developer API stage
########################################################################################################################


class MarvelAPICharacter(models.Model):
    id = models.IntegerField(primary_key=True, help_text='The unique ID of the character resource.')
    name = models.TextField(blank=True, help_text='The name of the character.')
    description = models.TextField(blank=True, help_text='A short bio or description of the character.')
    modified = models.DateTimeField(null=True, help_text='The date the resource was most recently modified.')
    resource_URI = models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')

    character = models.ForeignKey(Character, null=True, on_delete=models.SET_NULL, related_name="marvel_api_chararcter")

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(MarvelAPICharacter, self).save(force_insert, force_update, using, update_fields)
        if self.character:
            self.character.fill_from_marvel_api(self)


class MarvelAPICreator(models.Model):
    id = models.IntegerField(primary_key=True, help_text='The unique ID of the creator resource.')
    first_name = models.TextField(blank=True, help_text='The first name of the creator.')
    middle_name = models.TextField(blank=True, help_text='The middle name of the creator.')
    last_name = models.TextField(blank=True, help_text='The last name of the creator.')
    suffix = models.TextField(blank=True, help_text='The suffix or honorific for the creator.')
    full_name = models.TextField(blank=True, help_text='The full name of the creator.')
    modified = models.DateTimeField(null=True, help_text='The date the resource was most recently modified.')
    resource_URI = models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')

    creator = models.ForeignKey(Creator, null=True, on_delete=models.SET_NULL, related_name="marvel_api_creator")

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(MarvelAPICreator, self).save(force_insert, force_update, using, update_fields)
        if self.creator:
            self.creator.fill_from_marvel_api(self)


class MarvelAPIEventCreator(models.Model):
    creator = models.ForeignKey(MarvelAPICreator, on_delete=models.CASCADE)
    event = models.ForeignKey('MarvelAPIEvent', on_delete=models.CASCADE)
    role = models.CharField(max_length=50)


class MarvelAPIEvent(models.Model):
    id = models.IntegerField(primary_key=True, help_text='The unique ID of the event resource.')
    title = models.TextField(blank=True, help_text='The title of the event.')
    description = models.TextField(blank=True, help_text='A description of the event.')
    resource_URI = models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')
    modified = models.DateTimeField(null=True, help_text='The date the resource was most recently modified.')
    start = models.DateField(null=True, help_text='The date of publication of the first issue in this event.')
    end = models.DateField(null=True, help_text='The date of publication of the last issue in this event.')
    characters = models.ManyToManyField(MarvelAPICharacter, related_name='events',
                                        help_text='Characters which appear in this event.')
    creators = models.ManyToManyField(MarvelAPICreator, through=MarvelAPIEventCreator, related_name='events',
                                      help_text='Creators whose work appears in this event.')

    event = models.ForeignKey(Event, null=True, on_delete=models.SET_NULL, related_name="marvel_api_event")

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(MarvelAPIEvent, self).save(force_insert, force_update, using, update_fields)
        if self.event:
            self.event.fill_from_marvel_api(self)


class MarvelAPISeriesCreator(models.Model):
    creator = models.ForeignKey(MarvelAPICreator, on_delete=models.CASCADE)
    series_fk = models.ForeignKey('MarvelAPISeries', on_delete=models.CASCADE)
    role = models.CharField(max_length=50)


class MarvelAPISeries(models.Model):
    id = models.IntegerField(primary_key=True, help_text='The unique ID of the series resource.')
    title = models.TextField(blank=True, help_text='The canonical title of the series.')
    description = models.TextField(blank=True, help_text='A description of the series.')
    resource_URI = models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')
    start_year = models.IntegerField(null=True, help_text='The first year of publication for the series.')
    end_year = models.IntegerField(null=True,
                                   help_text='The last year of publication for the series '
                                             '(conventionally, 2099 for ongoing series).')
    rating = models.TextField(blank=True, help_text='The age-appropriateness rating for the series.')
    series_type = models.CharField(max_length=100, blank=True)
    modified = models.DateTimeField(null=True, help_text='The date the resource was most recently modified.')
    events = models.ManyToManyField(MarvelAPIEvent, related_name='series',
                                    help_text='Events which take place in comics in this series.')
    characters = models.ManyToManyField(MarvelAPICharacter, related_name='series',
                                        help_text='Characters which appear in comics in this series.')
    creators = models.ManyToManyField(MarvelAPICreator, through=MarvelAPISeriesCreator, related_name='series',
                                      help_text='Creators whose work appears in comics in this series.')

    ignore = models.BooleanField(default=False)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(MarvelAPISeries, self).save(force_insert, force_update, using, update_fields)
        if self.db_title:
            self.db_title.fill_from_marvel_api(self)


class MarvelAPIComicsCreator(models.Model):
    creator = models.ForeignKey(MarvelAPICreator, on_delete=models.CASCADE)
    comics_fk = models.ForeignKey('MarvelAPIComics', on_delete=models.CASCADE)
    role = models.CharField(max_length=50)


class MarvelAPIComics(models.Model):
    id = models.IntegerField(primary_key=True, help_text='The unique ID of the comic resource.')
    title = models.TextField(blank=True, help_text='The canonical title of the comic.')
    issue_number = models.FloatField(null=True,
                                       help_text='The number of the issue in the series '
                                                 '(will generally be 0 for collection formats).')
    description = models.TextField(blank=True, help_text='The preferred description of the comic.')
    modified = models.DateTimeField(null=True, help_text='The date the resource was most recently modified.')
    page_count = models.IntegerField(null=True, help_text='The number of story pages in the comic.')
    resource_URI = models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')
    creators = models.ManyToManyField(MarvelAPICreator, through=MarvelAPIComicsCreator, related_name='comics',
                                      help_text='Creators associated with this comic.')
    characters = models.ManyToManyField(MarvelAPICharacter, related_name='comics',
                                        help_text='Characters which appear in this comic.')
    events = models.ManyToManyField(MarvelAPIEvent, related_name='comics',
                                    help_text='Events in which this comic appears.')
    series = models.ForeignKey(MarvelAPISeries, related_name='comics', on_delete=models.CASCADE,
                               help_text='Series to which this comic belongs.')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(MarvelAPIComics, self).save(force_insert, force_update, using, update_fields)
        if self.db_issue:
            self.db_issue.fill_from_marvel_api(self)


class MarvelAPIDate(models.Model):
    type = models.CharField(max_length=30)
    date = models.DateTimeField()
    comics = models.ForeignKey(MarvelAPIComics, related_name='dates', on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('type', 'date', 'comics'),
        )


class MarvelAPISiteUrl(models.Model):
    type = models.CharField(max_length=100, help_text='A text identifier for the URL.')
    url = models.URLField(max_length=500, help_text='A full URL (including scheme, domain, and path).')
    character = models.ForeignKey(MarvelAPICharacter, null=True, on_delete=models.SET_NULL, related_name='urls')
    creator = models.ForeignKey(MarvelAPICreator, null=True, on_delete=models.SET_NULL, related_name='urls')
    event = models.ForeignKey(MarvelAPIEvent, null=True, on_delete=models.SET_NULL, related_name='urls')
    comics = models.ForeignKey(MarvelAPIComics, null=True, on_delete=models.SET_NULL, related_name='urls')
    series = models.ForeignKey(MarvelAPISeries, null=True, on_delete=models.SET_NULL, related_name='urls')


class MarvelAPIImage(models.Model):
    path = models.URLField(max_length=500, help_text='The directory path of to the image.')
    extension = models.CharField(max_length=10, help_text='The file extension for the image.')
    character = models.OneToOneField(MarvelAPICharacter, null=True, on_delete=models.SET_NULL,
                                     related_name='image')
    creator = models.OneToOneField(MarvelAPICreator, null=True, on_delete=models.SET_NULL, related_name='image')
    event = models.OneToOneField(MarvelAPIEvent, null=True, on_delete=models.SET_NULL, related_name='image')
    comics = models.OneToOneField(MarvelAPIComics, null=True, on_delete=models.SET_NULL, related_name='image')
    series = models.OneToOneField(MarvelAPISeries, null=True, on_delete=models.SET_NULL, related_name='image')


########################################################################################################################
# System & Profiles
########################################################################################################################


class ReadIssue(models.Model):
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    read_date = models.DateField(auto_now=True)

    class Meta:
        unique_together = (("profile", "issue"), )


class ReadingListIssue(models.Model):
    reading_list = models.ForeignKey('ReadingList', on_delete=models.CASCADE, db_column="readinglist_id")
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, db_column="issue_id")
    order = models.IntegerField(default=0)

    class Meta:
        db_table = "comics_db_readinglist_issues"

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(ReadingListIssue, self).save(force_insert, force_update, using, update_fields)


class ReadingList(models.Model):
    SORTING_CHOICES = (
        ('DEFAULT', 'Order by title and issue number'),
        ('MANUAL', 'Manual ordering')
    )
    owner = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='reading_lists')
    name = models.CharField(max_length=100)
    desc = models.TextField(blank=True)
    issues = models.ManyToManyField(Issue, related_name='reading_lists', through=ReadingListIssue)
    slug = models.SlugField(allow_unicode=True, max_length=500, unique=True)
    sorting = models.CharField(max_length=20, choices=SORTING_CHOICES, default="DEFAULT")

    @property
    def file_size(self):
        return self.issues.aggregate(file_size=Sum('file_size'))['file_size']

    @property
    def site_link(self):
        return reverse('site-user-reading-list', args=(self.slug,))

    def __str__(self):
        return "[{0.owner.user.username}] {0.name}".format(self)

    def get_slug(self):
        return slugify(str(self), allow_unicode=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(ReadingList, self).save(force_insert, force_update, using, update_fields)

    class Meta:
        unique_together = (('owner', 'name'),)


class Profile(models.Model):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    unlimited_api = models.BooleanField(default=False)
    read_issues = models.ManyToManyField(Issue, through=ReadIssue, related_name="readers")


class AppToken(models.Model):
    app_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    token = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="app_tokens")

    class Meta:
        unique_together = (("user", "app_name"),)
