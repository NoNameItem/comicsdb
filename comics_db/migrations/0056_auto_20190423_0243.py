# Generated by Django 2.2 on 2019-04-22 23:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0055_auto_20190422_2203'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='marvelapidate',
            unique_together={('type', 'date', 'comics')},
        ),
    ]
