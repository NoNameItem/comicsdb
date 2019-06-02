# Generated by Django 2.2 on 2019-06-02 01:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0002_auto_20190601_0654'),
    ]

    operations = [
        migrations.AddField(
            model_name='readinglist',
            name='sorting',
            field=models.CharField(choices=[('DEFAULT', 'Order by title und issue number'), ('MANUAL', 'Manual ordering')], default='DEFAULT', max_length=20),
        ),
    ]
