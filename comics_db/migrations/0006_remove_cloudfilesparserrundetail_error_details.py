# Generated by Django 2.1.7 on 2019-03-01 21:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0005_cloudfilesparserrundetail_created'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cloudfilesparserrundetail',
            name='error_details',
        ),
    ]
