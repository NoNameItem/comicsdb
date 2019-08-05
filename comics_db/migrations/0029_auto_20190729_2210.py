# Generated by Django 2.2.3 on 2019-07-29 19:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0028_auto_20190729_2129'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='marvelapititlemergeparserrundetail',
            name='api_comics',
        ),
        migrations.RemoveField(
            model_name='marvelapititlemergeparserrundetail',
            name='db_issue',
        ),
        migrations.AddField(
            model_name='marvelapititlemergeparserrundetail',
            name='api_title',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPISeries'),
        ),
        migrations.AddField(
            model_name='marvelapititlemergeparserrundetail',
            name='db_title',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='comics_db.Title'),
        ),
        migrations.AlterField(
            model_name='parserrun',
            name='parser',
            field=models.CharField(choices=[('BASE', 'Base parser'), ('CLOUD_FILES', 'Cloud files parser'), ('MARVEL_API', 'Marvel API parser'), ('MARVEL_API_CREATOR_MERGE', 'Marvel API creator merge'), ('MARVEL_API_CHARACTER_MERGE', 'Marvel API character merge'), ('MARVEL_API_EVENT_MERGE', 'Marvel API event merge'), ('MARVEL_API_TITLE_MERGE', 'Marvel API title merge'), ('MARVEL_API_ISSUE_MERGE', 'Marvel API comics merge')], default='BASE', max_length=30),
        ),
    ]