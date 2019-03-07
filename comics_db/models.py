from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django.contrib.auth.models import User
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

    class Meta:
        ordering = ["-start"]


class ParserRunDetail(models.Model):
    STATUS_CHOICES = (
        ("RUNNING", "Running"),
        ("SUCCESS", "Successfully ended"),
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


########################################################################################################################
# Comics Info
########################################################################################################################


class Publisher(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Creator(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    photo = models.ImageField(null=True)
    birth_date = models.DateField(null=True)
    death_date = models.DateField(null=True)

    def __str__(self):
        return self.name


class Universe(models.Model):
    name = models.CharField(max_length=100)
    desc = models.TextField(blank=True)
    publisher = models.ForeignKey(Publisher, on_delete=models.PROTECT, related_name="universes")

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


class Title(models.Model):
    name = models.CharField(max_length=500)
    publisher = models.ForeignKey(Publisher, on_delete=models.PROTECT, related_name="titles")
    universe = models.ForeignKey(Universe, on_delete=models.PROTECT, null=True, related_name="titles")
    title_type = models.ForeignKey(TitleType, on_delete=models.PROTECT, related_name="titles")

    def __str__(self):
        return "[{0.publisher.name}, {0.universe.name}, {0.title_type.name}] {0.name}".format(self)

    class Meta:
        unique_together = (("name", "publisher", "universe", "title_type"),)
        ordering = ["publisher", "universe", "name"]


class Issue(models.Model):
    name = models.CharField(max_length=500)
    number = models.IntegerField(null=True)
    desc = models.TextField(blank=True)
    title = models.ForeignKey(Title, on_delete=models.CASCADE, related_name="issues")
    publish_date = models.DateField()

    writers = models.ManyToManyField(Creator, related_name="written_issues")
    pencilers = models.ManyToManyField(Creator, related_name="drawn_issues")

    main_cover = models.ImageField(null=True)
    link = models.URLField(max_length=1000, unique=True)

    tags = models.ManyToManyField(Tag, related_name="issues")

    created_dt = models.DateTimeField(auto_now_add=True)
    modified_dt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "[{0.title.publisher.name}, {0.title.universe.name}, {0.publish_date.year}] {0.name}".format(self)

    @property
    def download_link(self):
        return escape_uri_path("{0}/{1.link}".format(settings.DO_PUBLIC_URL, self))

    class Meta:
        unique_together = (("name", "title", "publish_date"),)
        ordering = ["title", "publish_date", "number"]


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
