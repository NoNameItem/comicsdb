# Generated by Django 2.2.3 on 2019-07-29 18:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comics_db', '0026_auto_20190729_2125'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marvelapiissuemergeparserrundetail',
            name='db_issue',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='comics_db.Issue'),
        ),
    ]
