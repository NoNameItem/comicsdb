# Generated by Django 2.1.7 on 2019-03-07 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0016_auto_20190307_1046'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apptoken',
            name='token',
            field=models.TextField(),
        ),
    ]
