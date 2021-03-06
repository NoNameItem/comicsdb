# Generated by Django 2.2 on 2019-06-01 03:53

import comics_db.fields
import comics_db.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    replaces = [('comics_db', '0001_initial'), ('comics_db', '0002_auto_20190301_0352'), ('comics_db', '0003_auto_20190301_2001'), ('comics_db', '0004_auto_20190301_2106'), ('comics_db', '0005_cloudfilesparserrundetail_created'), ('comics_db', '0006_remove_cloudfilesparserrundetail_error_details'), ('comics_db', '0007_cloudfilesparserrundetail_error_stack'), ('comics_db', '0008_auto_20190302_0054'), ('comics_db', '0009_auto_20190302_0137'), ('comics_db', '0010_auto_20190302_0145'), ('comics_db', '0011_auto_20190302_0146'), ('comics_db', '0012_auto_20190303_0540'), ('comics_db', '0013_auto_20190303_0616'), ('comics_db', '0014_auto_20190303_0848'), ('comics_db', '0015_auto_20190306_0958'), ('comics_db', '0016_auto_20190307_1046'), ('comics_db', '0017_auto_20190307_1102'), ('comics_db', '0018_auto_20190307_1517'), ('comics_db', '0019_auto_20190308_0707'), ('comics_db', '0020_parserrunparameter'), ('comics_db', '0021_auto_20190308_1311'), ('comics_db', '0022_publisher_logo'), ('comics_db', '0023_auto_20190310_2138'), ('comics_db', '0024_publisher_slug'), ('comics_db', '0025_auto_20190311_0947'), ('comics_db', '0026_auto_20190311_0952'), ('comics_db', '0027_auto_20190311_0958'), ('comics_db', '0028_auto_20190311_1005'), ('comics_db', '0029_issue_slug'), ('comics_db', '0030_auto_20190311_1012'), ('comics_db', '0031_publisher_poster'), ('comics_db', '0032_auto_20190311_1733'), ('comics_db', '0033_auto_20190311_1916'), ('comics_db', '0034_auto_20190313_1823'), ('comics_db', '0035_title_path_key'), ('comics_db', '0036_auto_20190313_2338'), ('comics_db', '0037_universe_poster'), ('comics_db', '0038_auto_20190315_0032'), ('comics_db', '0039_issue_page_count'), ('comics_db', '0040_auto_20190318_0104'), ('comics_db', '0041_auto_20190318_0136'), ('comics_db', '0042_auto_20190320_1537'), ('comics_db', '0043_auto_20190320_1635'), ('comics_db', '0044_parserrunparams'), ('comics_db', '0045_remove_parserrun_processed'), ('comics_db', '0046_auto_20190324_0412'), ('comics_db', '0047_auto_20190324_2036'), ('comics_db', '0048_auto_20190401_2134'), ('comics_db', '0049_readinglist_slug'), ('comics_db', '0050_auto_20190415_1525'), ('comics_db', '0051_remove_marvelapicomics_format'), ('comics_db', '0052_auto_20190421_1502'), ('comics_db', '0053_marvelapicomics_creators'), ('comics_db', '0054_auto_20190422_2157'), ('comics_db', '0055_auto_20190422_2203'), ('comics_db', '0056_auto_20190423_0243')]

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('knox', '0006_auto_20160818_0932'),
    ]

    operations = [
        migrations.CreateModel(
            name='Creator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500)),
                ('bio', models.TextField(blank=True)),
                ('photo', models.ImageField(null=True, upload_to='')),
                ('marvel_api_id', models.IntegerField(null=True)),
                ('slug', models.SlugField(allow_unicode=True, default='', max_length=500, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Publisher',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('logo', comics_db.fields.ThumbnailImageField(null=True, upload_to=comics_db.models.get_publisher_logo_name)),
                ('desc', models.TextField(blank=True)),
                ('slug', models.SlugField(allow_unicode=True, max_length=500, unique=True)),
                ('poster', comics_db.fields.ThumbnailImageField(null=True, upload_to=comics_db.models.get_publisher_poster_name)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='TitleType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Universe',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('desc', models.TextField(blank=True)),
                ('publisher', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='universes', to='comics_db.Publisher')),
                ('slug', models.SlugField(allow_unicode=True, max_length=500, unique=True)),
                ('poster', comics_db.fields.ThumbnailImageField(null=True, upload_to=comics_db.models.get_universe_poster_name)),
            ],
            options={
                'unique_together': {('name', 'publisher')},
                'ordering': ['publisher', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Title',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500)),
                ('publisher', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='titles', to='comics_db.Publisher')),
                ('title_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='titles', to='comics_db.TitleType')),
                ('universe', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='titles', to='comics_db.Universe')),
                ('slug', models.SlugField(allow_unicode=True, max_length=500, unique=True)),
                ('desc', models.TextField(blank=True)),
                ('image', models.ImageField(null=True, upload_to='title_image')),
                ('marvel_api_id', models.IntegerField(null=True)),
                ('marvel_api_status', models.CharField(choices=[('NEW', 'New'), ('NO_ID', "Can't find ID"), ('ID_GET_DATA', 'ID found, need to get data'), ('PROCESSED', 'Processed')], default='NEW', max_length=30)),
            ],
            options={
                'unique_together': {('name', 'publisher', 'universe', 'title_type')},
                'ordering': ['publisher', 'universe', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Issue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500)),
                ('number', models.IntegerField(null=True)),
                ('desc', models.TextField(blank=True)),
                ('publish_date', models.DateField()),
                ('main_cover', models.ImageField(null=True, upload_to='issue_cover')),
                ('link', models.URLField(max_length=1000, unique=True)),
                ('tags', models.ManyToManyField(related_name='issues', to='comics_db.Tag')),
                ('title', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='issues', to='comics_db.Title')),
                ('created_dt', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('modified_dt', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(allow_unicode=True, max_length=500, unique=True)),
                ('marvel_api_id', models.IntegerField(null=True)),
                ('marvel_api_status', models.CharField(choices=[('NEW', 'New'), ('NO_ID', "Can't find ID"), ('ID_GET_DATA', 'ID found, need to get data'), ('PROCESSED', 'Processed')], default='NEW', max_length=30)),
                ('marvel_detail_link', models.URLField(blank=True, max_length=1000)),
                ('marvel_purchase_link', models.URLField(blank=True, max_length=1000)),
            ],
            options={
                'order_with_respect_to': None,
                'ordering': ['title', 'publish_date', 'number'],
                'unique_together': {('name', 'title', 'publish_date')},
            },
        ),
        migrations.CreateModel(
            name='ParserRun',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('parser', models.CharField(choices=[('BASE', 'Base parser'), ('CLOUD_FILES', 'Cloud files parser'), ('MARVEL_API', 'Marvel API parser')], default='BASE', max_length=30)),
                ('start', models.DateTimeField(default=django.utils.timezone.now)),
                ('end', models.DateTimeField(null=True)),
                ('status', models.CharField(choices=[('COLLECTING', 'Collecting data'), ('RUNNING', 'Running'), ('SUCCESS', 'Successfully ended'), ('ENDED_WITH_ERRORS', 'Ended with errors'), ('API_THROTTLE', 'API rate limit has been surpassed.'), ('CRITICAL_ERROR', 'Critical Error'), ('INVALID_PARSER', 'Invalid parser implementation')], default='COLLECTING', max_length=30)),
                ('error', models.TextField(blank=True)),
                ('items_count', models.IntegerField(null=True)),
                ('error_detail', models.TextField(blank=True)),
                ('celery_task_id', models.CharField(max_length=100, null=True)),
            ],
            options={
                'ordering': ['-start'],
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unlimited_api', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AppToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('token', models.TextField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='app_tokens', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'app_name')},
            },
        ),
        migrations.CreateModel(
            name='CloudFilesParserRunDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(default=django.utils.timezone.now)),
                ('end', models.DateTimeField(null=True)),
                ('status', models.CharField(choices=[('RUNNING', 'Running'), ('SUCCESS', 'Success'), ('ERROR', 'Error')], default='RUNNING', max_length=30)),
                ('error', models.TextField(blank=True)),
                ('file_key', models.TextField()),
                ('regex', models.TextField()),
                ('groups', models.TextField(blank=True)),
                ('issue', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='comics_db.Issue')),
                ('parser_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cloudfilesparserrundetails', to='comics_db.ParserRun')),
                ('created', models.BooleanField(default=False)),
                ('error_detail', models.TextField(blank=True)),
            ],
            options={
                'abstract': False,
                'ordering': ['parser_run', '-start'],
            },
        ),
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500, unique=True)),
                ('desc', models.TextField(blank=True)),
                ('image', models.ImageField(null=True, upload_to='character')),
                ('marvel_api_id', models.IntegerField(null=True)),
                ('marvel_detail_link', models.URLField(blank=True, max_length=1000)),
                ('issues', models.ManyToManyField(related_name='characters', to='comics_db.Issue')),
                ('titles', models.ManyToManyField(related_name='characters', to='comics_db.Title')),
                ('slug', models.SlugField(allow_unicode=True, default='', max_length=500, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='TitleCreator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=100)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.Creator')),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.Title')),
            ],
        ),
        migrations.CreateModel(
            name='IssueCreator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=100)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.Creator')),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.Issue')),
            ],
        ),
        migrations.AddField(
            model_name='issue',
            name='creators',
            field=models.ManyToManyField(related_name='issues', through='comics_db.IssueCreator', to='comics_db.Creator'),
        ),
        migrations.AddField(
            model_name='title',
            name='creators',
            field=models.ManyToManyField(related_name='titles', through='comics_db.TitleCreator', to='comics_db.Creator'),
        ),
        migrations.CreateModel(
            name='MarvelEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('desc', models.TextField(blank=True)),
                ('image', models.ImageField(null=True, upload_to='event-image')),
                ('detail_link', models.URLField(blank=True, max_length=1000)),
                ('start', models.DateField(null=True)),
                ('end', models.DateField(null=True)),
                ('characters', models.ManyToManyField(related_name='events', to='comics_db.Character')),
                ('creators', models.ManyToManyField(related_name='events', to='comics_db.Creator')),
                ('issues', models.ManyToManyField(related_name='events', to='comics_db.Issue')),
                ('titles', models.ManyToManyField(related_name='events', to='comics_db.Title')),
                ('slug', models.SlugField(allow_unicode=True, default='', max_length=500, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPICharacter',
            fields=[
                ('id', models.IntegerField(help_text='The unique ID of the character resource.', primary_key=True, serialize=False)),
                ('name', models.TextField(blank=True, help_text='The name of the character.')),
                ('description', models.TextField(blank=True, help_text='A short bio or description of the character.')),
                ('modified', models.DateTimeField(help_text='The date the resource was most recently modified.', null=True)),
                ('resource_URI', models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPIComics',
            fields=[
                ('id', models.IntegerField(help_text='The unique ID of the comic resource.', primary_key=True, serialize=False)),
                ('title', models.TextField(blank=True, help_text='The canonical title of the comic.')),
                ('issue_number', models.IntegerField(help_text='The number of the issue in the series (will generally be 0 for collection formats).', null=True)),
                ('description', models.TextField(blank=True, help_text='The preferred description of the comic.')),
                ('modified', models.DateField(help_text='The date the resource was most recently modified.', null=True)),
                ('format', models.TextField(blank=True, help_text='The publication format of the comic e.g. comic, hardcover, trade paperback.')),
                ('page_count', models.IntegerField(help_text='The number of story pages in the comic.', null=True)),
                ('resource_URI', models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')),
                ('characters', models.ManyToManyField(help_text='Characters which appear in this comic.', related_name='comics', to='comics_db.MarvelAPICharacter')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPICreator',
            fields=[
                ('id', models.IntegerField(help_text='The unique ID of the creator resource.', primary_key=True, serialize=False)),
                ('first_name', models.TextField(blank=True, help_text='The first name of the creator.')),
                ('middle_name', models.TextField(blank=True, help_text='The middle name of the creator.')),
                ('last_name', models.TextField(blank=True, help_text='The last name of the creator.')),
                ('suffix', models.TextField(blank=True, help_text='The suffix or honorific for the creator.')),
                ('full_name', models.TextField(blank=True, help_text='The full name of the creator.')),
                ('modified', models.DateTimeField(help_text='The date the resource was most recently modified.', null=True)),
                ('resource_URI', models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPIEvent',
            fields=[
                ('id', models.IntegerField(help_text='The unique ID of the event resource.', primary_key=True, serialize=False)),
                ('title', models.TextField(blank=True, help_text='The title of the event.')),
                ('description', models.TextField(blank=True, help_text='A description of the event.')),
                ('resource_URI', models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')),
                ('modified', models.DateTimeField(help_text='The date the resource was most recently modified.', null=True)),
                ('start', models.DateField(help_text='The date of publication of the first issue in this event.', null=True)),
                ('end', models.DateField(help_text='The date of publication of the last issue in this event.', null=True)),
                ('characters', models.ManyToManyField(help_text='Characters which appear in this event.', related_name='events', to='comics_db.MarvelAPICharacter')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPIEventCreator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=50)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPICreator')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPIEvent')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPISeries',
            fields=[
                ('id', models.IntegerField(help_text='The unique ID of the series resource.', primary_key=True, serialize=False)),
                ('title', models.TextField(blank=True, help_text='The canonical title of the series.')),
                ('description', models.TextField(blank=True, help_text='A description of the series.')),
                ('resource_URI', models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')),
                ('start_year', models.IntegerField(help_text='The first year of publication for the series.', null=True)),
                ('end_year', models.IntegerField(help_text='The last year of publication for the series (conventionally, 2099 for ongoing series).', null=True)),
                ('rating', models.TextField(blank=True, help_text='The age-appropriateness rating for the series.')),
                ('modified', models.DateTimeField(help_text='The date the resource was most recently modified.', null=True)),
                ('characters', models.ManyToManyField(help_text='Characters which appear in comics in this series.', related_name='series', to='comics_db.MarvelAPICharacter')),
                ('events', models.ManyToManyField(help_text='Events which take place in comics in this series.', related_name='series', to='comics_db.MarvelAPIEvent')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPISeriesCreator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=50)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPICreator')),
                ('series_fk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPISeries')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPIComicsCreator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=50)),
                ('comics_fk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPIComics')),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPICreator')),
            ],
        ),
        migrations.AddField(
            model_name='marvelapicomics',
            name='events',
            field=models.ManyToManyField(help_text='Events in which this comic appears.', related_name='comics', to='comics_db.MarvelAPIEvent'),
        ),
        migrations.AddField(
            model_name='marvelapicomics',
            name='series',
            field=models.ForeignKey(help_text='Series to which this comic belongs.', on_delete=django.db.models.deletion.CASCADE, related_name='comics', to='comics_db.MarvelAPISeries'),
        ),
        migrations.AlterField(
            model_name='issue',
            name='main_cover',
            field=comics_db.fields.ThumbnailImageField(null=True, upload_to='issue_cover'),
        ),
        migrations.AlterField(
            model_name='title',
            name='image',
            field=comics_db.fields.ThumbnailImageField(null=True, upload_to='title_image'),
        ),
        migrations.AddField(
            model_name='issue',
            name='page_count',
            field=models.IntegerField(null=True),
        ),
        migrations.CreateModel(
            name='ReadIssue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read_date', models.DateField(auto_now=True)),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.Issue')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.Profile')),
            ],
            options={
                'unique_together': {('profile', 'issue')},
            },
        ),
        migrations.AddField(
            model_name='profile',
            name='read_issues',
            field=models.ManyToManyField(related_name='readers', through='comics_db.ReadIssue', to='comics_db.Issue'),
        ),
        migrations.AddField(
            model_name='title',
            name='path_key',
            field=models.CharField(max_length=500),
        ),
        migrations.AlterUniqueTogether(
            name='title',
            unique_together={('path_key', 'publisher', 'universe', 'title_type'), ('name', 'publisher', 'universe', 'title_type')},
        ),
        migrations.CreateModel(
            name='ParserRunParams',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('val', models.TextField(blank=True)),
                ('parser_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='comics_db.ParserRun')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.AlterModelOptions(
            name='issue',
            options={'ordering': ['title', 'number']},
        ),
        migrations.AlterField(
            model_name='issue',
            name='main_cover',
            field=comics_db.fields.ThumbnailImageField(null=True, upload_to=comics_db.models.get_issue_cover_name),
        ),
        migrations.AlterField(
            model_name='title',
            name='image',
            field=comics_db.fields.ThumbnailImageField(null=True, upload_to=comics_db.models.get_title_image_name),
        ),
        migrations.AlterField(
            model_name='title',
            name='universe',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='titles', to='comics_db.Universe'),
        ),
        migrations.CreateModel(
            name='ReadingList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('desc', models.TextField(blank=True)),
                ('issues', models.ManyToManyField(related_name='reading_lists', to='comics_db.Issue')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reading_lists', to='comics_db.Profile')),
                ('slug', models.SlugField(allow_unicode=True, default='', max_length=500, unique=True)),
            ],
            options={
                'unique_together': {('owner', 'name')},
            },
        ),
        migrations.AlterField(
            model_name='marvelapicomics',
            name='modified',
            field=models.DateTimeField(help_text='The date the resource was most recently modified.', null=True),
        ),
        migrations.CreateModel(
            name='MarvelAPIParserRunDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(default=django.utils.timezone.now)),
                ('end', models.DateTimeField(null=True)),
                ('status', models.CharField(choices=[('RUNNING', 'Running'), ('SUCCESS', 'Success'), ('ERROR', 'Error')], default='RUNNING', max_length=30)),
                ('error', models.TextField(blank=True)),
                ('error_detail', models.TextField(blank=True)),
                ('entity_type', models.CharField(choices=[('COMICS', 'Comics'), ('CHARACTER', 'Character'), ('CREATOR', 'Creator'), ('EVENT', 'Event'), ('SERIES', 'Series')], max_length=10)),
                ('action', models.CharField(choices=[('GET', 'Getting data from API'), ('PROCESS', 'Processing data')], max_length=10)),
                ('entity_id', models.IntegerField(null=True)),
                ('data', models.TextField(blank=True)),
                ('parser_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marvelapiparserrundetails', to='comics_db.ParserRun')),
            ],
            options={
                'ordering': ['parser_run', '-start'],
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='marvelapicomics',
            name='format',
        ),
        migrations.CreateModel(
            name='MarvelAPIImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.URLField(help_text='The directory path of to the image.', max_length=500)),
                ('extension', models.CharField(help_text='The file extension for the image.', max_length=10)),
                ('character', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail', to='comics_db.MarvelAPICharacter')),
                ('comics', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail', to='comics_db.MarvelAPIComics')),
                ('creator', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail', to='comics_db.MarvelAPICreator')),
                ('event', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail', to='comics_db.MarvelAPIEvent')),
                ('series', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail', to='comics_db.MarvelAPISeries')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPISiteUrl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(help_text='A text identifier for the URL.', max_length=100)),
                ('url', models.URLField(help_text='A full URL (including scheme, domain, and path).', max_length=500)),
                ('character', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='urls', to='comics_db.MarvelAPICharacter')),
                ('comics', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='urls', to='comics_db.MarvelAPIComics')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='urls', to='comics_db.MarvelAPICreator')),
                ('event', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='urls', to='comics_db.MarvelAPIEvent')),
                ('series', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='urls', to='comics_db.MarvelAPISeries')),
            ],
        ),
        migrations.AddField(
            model_name='marvelapicomics',
            name='creators',
            field=models.ManyToManyField(help_text='Creators associated with this comic.', related_name='comics', through='comics_db.MarvelAPIComicsCreator', to='comics_db.MarvelAPICreator'),
        ),
        migrations.AddField(
            model_name='marvelapievent',
            name='creators',
            field=models.ManyToManyField(help_text='Creators whose work appears in this event.', related_name='events', through='comics_db.MarvelAPIEventCreator', to='comics_db.MarvelAPICreator'),
        ),
        migrations.AddField(
            model_name='marvelapiseries',
            name='creators',
            field=models.ManyToManyField(help_text='Creators whose work appears in comics in this series.', related_name='series', through='comics_db.MarvelAPISeriesCreator', to='comics_db.MarvelAPICreator'),
        ),
        migrations.CreateModel(
            name='MarvelAPIDate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=30)),
                ('date', models.DateTimeField()),
                ('comics', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dates', to='comics_db.MarvelAPIComics')),
            ],
            options={
                'unique_together': {('type', 'date', 'comics')},
            },
        ),
    ]
