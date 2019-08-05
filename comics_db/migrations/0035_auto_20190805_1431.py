# Generated by Django 2.2.4 on 2019-08-05 11:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0034_auto_20190804_0122'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='character',
            options={'ordering': ('name',)},
        ),
        migrations.AddField(
            model_name='character',
            name='api_image',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='creator',
            name='api_image',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='event',
            name='api_image',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='issue',
            name='api_image',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='title',
            name='api_image',
            field=models.BooleanField(default=False),
        ),
    ]