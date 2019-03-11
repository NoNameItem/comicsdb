from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django.contrib.auth.models import User
from django.utils.text import slugify
from knox.models import AuthToken

from comicsdb import settings


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
        ("CRITICAL_ERROR", "Critical Error"),
        ("INVALID_PARSER", "Invalid parser implementation")
    )

    parser = models.CharField(max_length=30, choices=PARSER_CHOICES, default=PARSER_CHOICES[0][0])
    start = models.DateTimeField(default=timezone.now)
    end = models.DateTimeField(null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    items_count = models.IntegerField(null=True)
    processed = models.IntegerField(null=True)
    error = models.TextField(blank=True)
    error_detail = models.TextField(blank=True)
    celery_task_id = models.CharField(max_length=100, blank=True)

    def inc_processed(self):
        if self.processed:
            self.processed += 1
        else:
            self.processed = 1
        self.save()

    @property
    def parser_name(self):
        return self.get_parser_display()

    @property
    def status_name(self):
        return self.get_status_display()

    @property
    def run_details_url(self):
        if self.parser == 'CLOUD_FILES':
            return reverse('parserrun-details-cloud', args=(self.id, ))
        return None

    @property
    def page(self):
        return reverse('parser-log-detail', args=(self.id, ))

    class Meta:
        ordering = ["-start"]


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


class Publisher(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(null=True, upload_to='publisher_logo')
    poster = models.ImageField(null=True, upload_to='publisher_poster')
    desc = models.TextField(blank=True)
    slug = models.SlugField(max_length=500, unique=True, allow_unicode=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name, allow_unicode=True)
        super(Publisher, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Creator(models.Model):
    name = models.CharField(max_length=500)
    bio = models.TextField(blank=True)
    photo = models.ImageField(null=True)

    # Marvel-specific fields
    marvel_api_id = models.IntegerField(null=True)

    def __str__(self):
        return self.name


class Universe(models.Model):
    name = models.CharField(max_length=100)
    desc = models.TextField(blank=True)
    slug = models.SlugField(max_length=500, unique=True, allow_unicode=True)

    publisher = models.ForeignKey(Publisher, on_delete=models.PROTECT, related_name="universes")

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = slugify(str(self), allow_unicode=True)
        super(Universe, self).save(force_insert, force_update, using, update_fields)

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


class Title(models.Model):
    name = models.CharField(max_length=500)
    desc = models.TextField(blank=True)
    image = models.ImageField(null=True, upload_to='title_image')
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
        self.slug = slugify(str(self), allow_unicode=True)
        super(Title, self).save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return "[{0.publisher.name}, {0.universe.name}, {0.title_type.name}] {0.name}".format(self)

    class Meta:
        unique_together = (("name", "publisher", "universe", "title_type"),)
        ordering = ["publisher", "universe", "name"]


class IssueCreator(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    issue = models.ForeignKey('Issue', on_delete=models.CASCADE)
    role = models.CharField(max_length=100)


class Issue(models.Model):
    name = models.CharField(max_length=500)
    number = models.IntegerField(null=True)
    desc = models.TextField(blank=True)
    publish_date = models.DateField()
    slug = models.SlugField(max_length=500, allow_unicode=True, unique=True)
    main_cover = models.ImageField(null=True, upload_to='issue_cover')
    link = models.URLField(max_length=1000, unique=True)

    title = models.ForeignKey(Title, on_delete=models.CASCADE, related_name="issues")
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
        self.slug = slugify(str(self), allow_unicode=True)
        super(Issue, self).save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return "[{0.title.publisher.name}, {0.title.universe.name}, {0.publish_date.year}] {0.name}".format(self)

    @property
    def download_link(self):
        return escape_uri_path("{0}/{1.link}".format(settings.DO_PUBLIC_URL, self))

    class Meta:
        unique_together = (("name", "title", "publish_date"),)
        ordering = ["title", "publish_date", "number"]


class Character(models.Model):
    name = models.CharField(max_length=500)
    desc = models.TextField(blank=True)
    image = models.ImageField(null=True, upload_to='character')

    titles = models.ManyToManyField(Title, related_name='characters')
    issues = models.ManyToManyField(Issue, related_name='characters')

    # Marvel-specific fields
    marvel_api_id = models.IntegerField(null=True)
    marvel_detail_link = models.URLField(max_length=1000, blank=True)


class MarvelEvent(models.Model):
    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True)
    image = models.ImageField(null=True, upload_to='event-image')
    detail_link = models.URLField(max_length=1000, blank=True)
    start = models.DateField(null=True)
    end = models.DateField(null=True)

    titles = models.ManyToManyField(Title, related_name='events')
    issues = models.ManyToManyField(Issue, related_name='events')
    characters = models.ManyToManyField(Character, related_name='events')
    creators = models.ManyToManyField(Creator, related_name='events')


########################################################################################################################
# System
########################################################################################################################


class Profile(models.Model):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    unlimited_api = models.BooleanField(default=False)


class AppToken(models.Model):
    app_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    token = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="app_tokens")

    class Meta:
        unique_together = (("user", "app_name"), )
