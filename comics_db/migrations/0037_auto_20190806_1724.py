# Generated by Django 2.2.4 on 2019-08-06 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0036_auto_20190806_1537'),
    ]

    operations = [
        migrations.AlterField(
            model_name='title',
            name='end_year',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='title',
            name='start_year',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]