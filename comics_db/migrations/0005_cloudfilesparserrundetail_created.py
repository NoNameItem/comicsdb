# Generated by Django 2.1.7 on 2019-03-01 20:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0004_auto_20190301_2106'),
    ]

    operations = [
        migrations.AddField(
            model_name='cloudfilesparserrundetail',
            name='created',
            field=models.BooleanField(default=False),
        ),
    ]
