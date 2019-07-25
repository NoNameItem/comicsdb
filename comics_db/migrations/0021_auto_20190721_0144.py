# Generated by Django 2.2.3 on 2019-07-20 22:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0020_auto_20190721_0104'),
    ]

    operations = [
        migrations.RenameField(
            model_name='marvelapititlemergeparserrundetail',
            old_name='db_event',
            new_name='db_title',
        ),
        migrations.AddField(
            model_name='title',
            name='possible_matches',
            field=models.ManyToManyField(related_name='db_possible_matches', to='comics_db.MarvelAPISeries'),
        ),
        migrations.AlterField(
            model_name='marvelapititlemergeparserrundetail',
            name='api_title',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='comics_db.MarvelAPISeries'),
        ),
    ]
