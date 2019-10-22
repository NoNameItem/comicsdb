# Generated by Django 2.2.4 on 2019-08-06 12:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0035_auto_20190805_1431'),
    ]

    operations = [
        migrations.AlterField(
            model_name='issue',
            name='marvel_api_comic',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='db_issues', to='comics_db.MarvelAPIComics'),
        ),
        migrations.AlterField(
            model_name='title',
            name='api_series',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='db_titles', to='comics_db.MarvelAPISeries'),
        ),
    ]