# Generated by Django 2.1.7 on 2019-03-11 07:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0028_auto_20190311_1005'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='slug',
            field=models.SlugField(allow_unicode=True, default='', max_length=500),
            preserve_default=False,
        ),
    ]
