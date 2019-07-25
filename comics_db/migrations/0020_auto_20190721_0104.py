# Generated by Django 2.2.3 on 2019-07-20 22:04

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0019_marvelapiseries_series_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='title',
            name='marvel_api_id',
        ),
        migrations.RemoveField(
            model_name='title',
            name='marvel_api_status',
        ),
        migrations.AddField(
            model_name='marvelapiseries',
            name='ignore',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='title',
            name='api_series',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='db_title', to='comics_db.MarvelAPISeries'),
        ),
        migrations.AlterField(
            model_name='parserrun',
            name='parser',
            field=models.CharField(choices=[('BASE', 'Base parser'), ('CLOUD_FILES', 'Cloud files parser'), ('MARVEL_API', 'Marvel API parser'), ('MARVEL_API_CREATOR_MERGE', 'Marvel API creator merge'), ('MARVEL_API_CHARACTER_MERGE', 'Marvel API character merge'), ('MARVEL_API_EVENT_MERGE', 'Marvel API event merge'), ('MARVEL_API_TITLE_MERGE', 'Marvel API title merge'), ('MARVEL_API_COMICS_MERGE', 'Marvel API comics merge')], default='BASE', max_length=30),
        ),
        migrations.CreateModel(
            name='MarvelAPITitleMergeParserRunDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(default=django.utils.timezone.now)),
                ('end', models.DateTimeField(null=True)),
                ('status', models.CharField(choices=[('RUNNING', 'Running'), ('SUCCESS', 'Success'), ('ERROR', 'Error')], default='RUNNING', max_length=30)),
                ('error', models.TextField(blank=True)),
                ('error_detail', models.TextField(blank=True)),
                ('created', models.BooleanField(default=False)),
                ('merge_result', models.CharField(blank=True, choices=[('SUCCESS', 'Success'), ('NOT_FOUND', 'Match not found'), ('DUPLICATES', 'Multiple matches')], max_length=20)),
                ('api_title', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPISeries')),
                ('db_event', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='comics_db.Title')),
                ('parser_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marvelapititlemergeparserrundetails', to='comics_db.ParserRun')),
            ],
            options={
                'ordering': ['parser_run', '-start'],
                'abstract': False,
            },
        ),
    ]
