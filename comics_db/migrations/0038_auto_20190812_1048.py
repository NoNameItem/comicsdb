# Generated by Django 2.2.4 on 2019-08-12 07:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0037_auto_20190806_1724'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='title',
            unique_together={('path_key', 'publisher', 'universe', 'title_type')},
        ),
    ]
