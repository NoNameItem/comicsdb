# Generated by Django 2.2.1 on 2019-06-06 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0007_auto_20190602_0717'),
    ]

    operations = [
        migrations.AlterField(
            model_name='issue',
            name='number',
            field=models.FloatField(null=True),
        ),
    ]