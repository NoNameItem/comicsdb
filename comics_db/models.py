from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django.contrib.auth.models import User
from django.utils.text import slugify
from knox.models import AuthToken

from comicsdb import settings
from comics_db.fields import ThumbnailImageField


# Create your models here.


########################################################################################################################
# Parsers
########################################################################################################################

class ParserRun(models.Model):
    PARSER_CHOICES = (
        ("BASE", "Base parser"),
        ("CLOUD_FILES", "Cloud files parser"),
    )

    STATUS_CHOICES = (
        ("RUNNING", "Running"),
        ("SUCCESS", "Successfully ended"),
        ("ENDED_WITH_ERRORS", "Ended with errors"),
        ("API_THROTTLE", "API rate limit has been surpassed."),
        ("CRITICAL_ERROR", "Critical Error"),
        ("INVALID_PARSER", "Invalid parser implementation")
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
        return None

    @property
    def page(self):
        return reverse('parser-log-detail', args=(self.id,))

    @property
    def success_count(self):
        if self.parser == 'CLOUD_FILES':
            details = self.cloudfilesparserrundetails
        else:
            return 0
        return details.filter(status='SUCCESS').count()

    @property
    def error_count(self):
        if self.parser == 'CLOUD_FILES':
            details = self.cloudfilesparserrundetails
        else:
            return 0
        return details.filter(status='ERROR').count()

    @property
    def processed(self):
        if self.parser == 'CLOUD_FILES':
            details = self.cloudfilesparserrundetails
        else:
            return 0
        return details.exclude(status='RUNNING').count()

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

    def save(self, *args, **kwargs):
        self.slug = self.get_slug()
        super(Publisher, self).save(*args, **kwargs)

    def get_slug(self):
        return slugify(self.name, allow_unicode=True)

    def __str__(self):
        return self.name

    @property
    def issue_count(self):
        return self.titles.aggregate(models.Count('issues'))['issues__count']

    class Meta:
        ordering = ["name"]


class Creator(models.Model):
    name = models.CharField(max_length=500)
    bio = models.TextField(blank=True)
    photo = models.ImageField(null=True)
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)

    # Marvel-specific fields
    marvel_api_id = models.IntegerField(null=True)

    def __str__(self):
        return self.name

    def get_slug(self):
        return slugify(self.name, allow_unicode=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Creator, self).save(force_insert, force_update, using, update_fields)


def get_universe_poster_name(instance, filename):
    return "universe_poster/{0}_poster.{1}".format(instance.name, filename.split('.')[-1])


class Universe(models.Model):
    name = models.CharField(max_length=100)
    desc = models.TextField(blank=True)
    slug = models.SlugField(max_length=500, unique=True, allow_unicode=True)
    poster = ThumbnailImageField(null=True, upload_to=get_universe_poster_name, thumb_width=520, thumb_height=200)

    publisher = models.ForeignKey(Publisher, on_delete=models.PROTECT, related_name="universes")

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Universe, self).save(force_insert, force_update, using, update_fields)

    def get_slug(self):
        return slugify(str(self), allow_unicode=True)

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
    issue = models.ForeignKey('Title', on_delete=models.CASCADE)
    role = models.CharField(max_length=100)


def get_title_image_name(instance, filename):
    return "title_image/{0}_image.{1}".format(instance.name, filename.split('.')[-1])


class Title(models.Model):
    name = models.CharField(max_length=500)
    path_key = models.CharField(max_length=500)
    desc = models.TextField(blank=True)
    image = ThumbnailImageField(null=True, upload_to=get_title_image_name, thumb_width=380)
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)

    publisher = models.ForeignKey(Publisher, on_delete=models.PROTECT, related_name="titles")
    universe = models.ForeignKey(Universe, on_delete=models.PROTECT, null=True, related_name="titles")
    title_type = models.ForeignKey(TitleType, on_delete=models.PROTECT, related_name="titles")
    creators = models.ManyToManyField(Creator, through=TitleCreator, related_name='titles')

    # Marvel-specific fields
    marvel_api_id = models.IntegerField(null=True)
    marvel_api_status = models.CharField(default='NEW', choices=MARVEL_API_STATUS_CHOICES, max_length=30)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Title, self).save(force_insert, force_update, using, update_fields)

    def get_slug(self):
        return slugify(str(self), allow_unicode=True)

    def __str__(self):
        return "[{0.publisher.name}, {0.universe.name}, {0.title_type.name}] {0.name}".format(self)

    @property
    def logo(self):
        return self.publisher.logo

    @property
    def site_link(self):
        return reverse('site-title-detail', args=(self.slug,))

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
    number = models.IntegerField(null=True)
    desc = models.TextField(blank=True)
    publish_date = models.DateField()
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)
    main_cover = ThumbnailImageField(null=True, upload_to=get_issue_cover_name, thumb_width=380)
    link = models.URLField(max_length=1000, unique=True)
    page_count = models.IntegerField(null=True)

    title = models.ForeignKey(Title, on_delete=models.CASCADE, related_name="issues", db_index=True)
    creators = models.ManyToManyField(Creator, through=IssueCreator, related_name='issues')
    tags = models.ManyToManyField(Tag, related_name="issues")

    created_dt = models.DateTimeField(auto_now_add=True)
    modified_dt = models.DateTimeField(auto_now=True)

    # Marvel-specific fields
    marvel_api_id = models.IntegerField(null=True)
    marvel_api_status = models.CharField(default='NEW', choices=MARVEL_API_STATUS_CHOICES, max_length=30)
    marvel_detail_link = models.URLField(max_length=1000, blank=True)
    marvel_purchase_link = models.URLField(max_length=1000, blank=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Issue, self).save(force_insert, force_update, using, update_fields)

    def get_slug(self):
        return slugify(self.link.replace('/', '_')[8:-4], allow_unicode=True)

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

    @property
    def logo(self):
        return self.title.publisher.logo

    class Meta:
        unique_together = (("name", "title", "publish_date"),)
        ordering = ["title", "number"]


class Character(models.Model):
    name = models.CharField(max_length=500, unique=True)
    desc = models.TextField(blank=True)
    image = models.ImageField(null=True, upload_to='character')
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)

    titles = models.ManyToManyField(Title, related_name='characters')
    issues = models.ManyToManyField(Issue, related_name='characters')

    # Marvel-specific fields
    marvel_api_id = models.IntegerField(null=True)
    marvel_detail_link = models.URLField(max_length=1000, blank=True)

    def get_slug(self):
        return slugify(str(self), allow_unicode=True)

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(Character, self).save(force_insert, force_update, using, update_fields)


class MarvelEvent(models.Model):
    name = models.CharField(max_length=200, unique=True)
    desc = models.TextField(blank=True)
    image = models.ImageField(null=True, upload_to='event-image')
    detail_link = models.URLField(max_length=1000, blank=True)
    start = models.DateField(null=True)
    end = models.DateField(null=True)
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)

    titles = models.ManyToManyField(Title, related_name='events')
    issues = models.ManyToManyField(Issue, related_name='events')
    characters = models.ManyToManyField(Character, related_name='events')
    creators = models.ManyToManyField(Creator, related_name='events')

    def get_slug(self):
        return slugify(str(self), allow_unicode=True)

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = self.get_slug()
        super(MarvelEvent, self).save(force_insert, force_update, using, update_fields)


########################################################################################################################
# Marvel Developer API stage
########################################################################################################################


class MarvelAPICharacter(models.Model):
    id = models.IntegerField(primary_key=True, help_text='The unique ID of the character resource.')
    name = models.TextField(blank=True, help_text='The name of the character.')
    description = models.TextField(blank=True, help_text='A short bio or description of the character.')
    modified = models.DateField(null=True, help_text='The date the resource was most recently modified.')
    resource_URI = models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')


class MarvelAPICreator(models.Model):
    id = models.IntegerField(primary_key=True, help_text='The unique ID of the creator resource.')
    first_name = models.TextField(blank=True, help_text='The first name of the creator.')
    middle_name = models.TextField(blank=True, help_text='The middle name of the creator.')
    last_name = models.TextField(blank=True, help_text='The last name of the creator.')
    suffix = models.TextField(blank=True, help_text='The suffix or honorific for the creator.')
    full_name = models.TextField(blank=True, help_text='The full name of the creator.')
    modified = models.DateField(null=True, help_text='The date the resource was most recently modified.')
    resource_URI = models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')


class MarvelAPIEventCreator(models.Model):
    creator = models.ForeignKey(MarvelAPICreator, on_delete=models.CASCADE)
    event = models.ForeignKey('MarvelAPIEvent', on_delete=models.CASCADE)
    role = models.CharField(max_length=50)


class MarvelAPIEvent(models.Model):
    id = models.IntegerField(primary_key=True, help_text='The unique ID of the event resource.')
    title = models.TextField(blank=True, help_text='The title of the event.')
    description = models.TextField(blank=True, help_text='A description of the event.')
    resource_URI = models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')
    modified = models.DateField(null=True, help_text='The date the resource was most recently modified.')
    start = models.DateField(null=True, help_text='The date of publication of the first issue in this event.')
    end = models.DateField(null=True, help_text='The date of publication of the last issue in this event.')
    characters = models.ManyToManyField(MarvelAPICharacter, related_name='events',
                                        help_text='Characters which appear in this event.')
    creators = models.ManyToManyField(MarvelAPIEventCreator, related_name='events',
                                      help_text='Creators whose work appears in this event.')


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
    modified = models.DateField(null=True, help_text='The date the resource was most recently modified.')
    events = models.ManyToManyField(MarvelAPIEvent, related_name='series',
                                    help_text='Events which take place in comics in this series.')
    characters = models.ManyToManyField(MarvelAPICharacter, related_name='series',
                                        help_text='Characters which appear in comics in this series.')
    creators = models.ManyToManyField(MarvelAPISeriesCreator, related_name='series',
                                      help_text='Creators whose work appears in comics in this series.')


class MarvelAPIComicsCreator(models.Model):
    creator = models.ForeignKey(MarvelAPICreator, on_delete=models.CASCADE)
    comics_fk = models.ForeignKey('MarvelAPIComics', on_delete=models.CASCADE)
    role = models.CharField(max_length=50)


class MarvelAPIComics(models.Model):
    id = models.IntegerField(primary_key=True, help_text='The unique ID of the comic resource.')
    title = models.TextField(blank=True, help_text='The canonical title of the comic.')
    issue_number = models.IntegerField(null=True,
                                       help_text='The number of the issue in the series '
                                                 '(will generally be 0 for collection formats).')
    description = models.TextField(blank=True, help_text='The preferred description of the comic.')
    modified = models.DateField(null=True, help_text='The date the resource was most recently modified.')
    format = models.TextField(blank=True,
                              help_text='The publication format of the comic e.g. comic, hardcover, trade paperback.')
    page_count = models.IntegerField(null=True, help_text='The number of story pages in the comic.')
    resource_URI = models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')
    creators = models.ManyToManyField(MarvelAPIComicsCreator, related_name='comics',
                                      help_text='Creators associated with this comic.')
    characters = models.ManyToManyField(MarvelAPICharacter, related_name='comics',
                                        help_text='Characters which appear in this comic.')
    events = models.ManyToManyField(MarvelAPIEvent, related_name='comics',
                                    help_text='Events in which this comic appears.')
    series = models.ForeignKey(MarvelAPISeries, related_name='comics', on_delete=models.CASCADE,
                               help_text='Series to which this comic belongs.')


class MarvelAPIDate(models.Model):
    type = models.CharField(max_length=30)
    date = models.DateField()
    comics = models.ForeignKey(MarvelAPIComics, related_name='dates', on_delete=models.CASCADE)


class MarvelAPISiteUrl(models.Model):
    type = models.CharField(max_length=100, help_text='A text identifier for the URL.')
    url = models.URLField(max_length=500, help_text='A full URL (including scheme, domain, and path).')
    character = models.ForeignKey(MarvelAPICharacter, null=True, on_delete=models.SET_NULL, related_name='urls')
    creator = models.ForeignKey(MarvelAPICreator, null=True, on_delete=models.SET_NULL, related_name='urls')
    event = models.ForeignKey(MarvelAPIEvent, null=True, on_delete=models.SET_NULL, related_name='urls')
    comics = models.ForeignKey(MarvelAPIComics, null=True, on_delete=models.SET_NULL, related_name='urls')


class MarvelAPIImage(models.Model):
    path = models.URLField(max_length=500, help_text='The directory path of to the image.')
    extension = models.CharField(max_length=10, help_text='The file extension for the image.')
    character = models.OneToOneField(MarvelAPICharacter, null=True, on_delete=models.SET_NULL,
                                     related_name='thumbnail')
    creator = models.OneToOneField(MarvelAPICreator, null=True, on_delete=models.SET_NULL, related_name='thumbnail')
    event = models.OneToOneField(MarvelAPIEvent, null=True, on_delete=models.SET_NULL, related_name='thumbnail')
    comics = models.OneToOneField(MarvelAPIComics, null=True, on_delete=models.SET_NULL, related_name='thumbnail')


########################################################################################################################
# System
########################################################################################################################


class ReadIssue(models.Model):
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    read_date = models.DateField(auto_now=True)

    class Meta:
        unique_together = (("profile", "issue"), )


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
