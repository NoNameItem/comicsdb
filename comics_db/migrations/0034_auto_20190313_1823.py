# Generated by Django 2.1.7 on 2019-03-13 15:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0033_auto_20190311_1916'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarvelAPICharacter',
            fields=[
                ('id', models.IntegerField(help_text='The unique ID of the character resource.', primary_key=True, serialize=False)),
                ('name', models.TextField(blank=True, help_text='The name of the character.')),
                ('description', models.TextField(blank=True, help_text='A short bio or description of the character.')),
                ('modified', models.DateField(help_text='The date the resource was most recently modified.', null=True)),
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
            name='MarvelAPIComicsCreator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=50)),
                ('comics_fk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPIComics')),
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
                ('modified', models.DateField(help_text='The date the resource was most recently modified.', null=True)),
                ('resource_URI', models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPIDate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=30)),
                ('date', models.DateField()),
                ('comics', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dates', to='comics_db.MarvelAPIComics')),
            ],
        ),
        migrations.CreateModel(
            name='MarvelAPIEvent',
            fields=[
                ('id', models.IntegerField(help_text='The unique ID of the event resource.', primary_key=True, serialize=False)),
                ('title', models.TextField(blank=True, help_text='The title of the event.')),
                ('description', models.TextField(blank=True, help_text='A description of the event.')),
                ('resource_URI', models.TextField(blank=True, help_text='The canonical URL identifier for this resource.')),
                ('modified', models.DateField(help_text='The date the resource was most recently modified.', null=True)),
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
            name='MarvelAPIImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.URLField(help_text='The directory path of to the image.', max_length=500)),
                ('extension', models.CharField(help_text='The file extension for the image.', max_length=10)),
                ('character', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail', to='comics_db.MarvelAPICharacter')),
                ('comics', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail', to='comics_db.MarvelAPIComics')),
                ('creator', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail', to='comics_db.MarvelAPICreator')),
                ('event', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail', to='comics_db.MarvelAPIEvent')),
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
                ('modified', models.DateField(help_text='The date the resource was most recently modified.', null=True)),
                ('characters', models.ManyToManyField(help_text='Characters which appear in comics in this series.', related_name='series', to='comics_db.MarvelAPICharacter')),
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
            name='MarvelAPISiteUrl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(help_text='A text identifier for the URL.', max_length=100)),
                ('url', models.URLField(help_text='A full URL (including scheme, domain, and path).', max_length=500)),
                ('character', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='urls', to='comics_db.MarvelAPICharacter')),
                ('comics', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='urls', to='comics_db.MarvelAPIComics')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='urls', to='comics_db.MarvelAPICreator')),
                ('event', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='urls', to='comics_db.MarvelAPIEvent')),
            ],
        ),
        migrations.AlterField(
            model_name='parserrun',
            name='status',
            field=models.CharField(choices=[('RUNNING', 'Running'), ('SUCCESS', 'Successfully ended'), ('ENDED_WITH_ERRORS', 'Ended with errors'), ('API_THROTTLE', 'API rate limit has been surpassed.'), ('CRITICAL_ERROR', 'Critical Error'), ('INVALID_PARSER', 'Invalid parser implementation')], default='RUNNING', max_length=30),
        ),
        migrations.AddField(
            model_name='marvelapiseries',
            name='creators',
            field=models.ManyToManyField(help_text='Creators whose work appears in comics in this series.', related_name='series', to='comics_db.MarvelAPISeriesCreator'),
        ),
        migrations.AddField(
            model_name='marvelapiseries',
            name='events',
            field=models.ManyToManyField(help_text='Events which take place in comics in this series.', related_name='series', to='comics_db.MarvelAPIEvent'),
        ),
        migrations.AddField(
            model_name='marvelapievent',
            name='creators',
            field=models.ManyToManyField(help_text='Creators whose work appears in this event.', related_name='events', to='comics_db.MarvelAPIEventCreator'),
        ),
        migrations.AddField(
            model_name='marvelapicomicscreator',
            name='creator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPICreator'),
        ),
        migrations.AddField(
            model_name='marvelapicomics',
            name='creators',
            field=models.ManyToManyField(help_text='Creators associated with this comic.', related_name='comics', to='comics_db.MarvelAPIComicsCreator'),
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
    ]
