# Generated by Django 2.2.4 on 2019-08-03 22:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0033_auto_20190804_0117'),
    ]

    operations = [
        migrations.RenameField(
            model_name='character',
            old_name='marvel_wiki_url',
            new_name='marvel_url',
        ),
        migrations.RenameField(
            model_name='event',
            old_name='marvel_api_url',
            new_name='marvel_url',
        ),
    ]