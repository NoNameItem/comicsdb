# Generated by Django 2.2 on 2019-06-02 01:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('comics_db', '0003_readinglist_sorting'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.CreateModel(
                name='ReadingListIssue',
                fields=[
                    ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('issue', models.ForeignKey(db_column='issue_id', on_delete=django.db.models.deletion.CASCADE,
                                                to='comics_db.Issue')),
                ],
                options={
                    'db_table': 'comics_db_readinglist_issues',
                },
            ),
            migrations.AlterField(
                model_name='readinglist',
                name='issues',
                field=models.ManyToManyField(related_name='reading_lists', through='comics_db.ReadingListIssue',
                                             to='comics_db.Issue'),
            ),
            migrations.AddField(
                model_name='readinglistissue',
                name='reading_list',
                field=models.ForeignKey(db_column='readinglist_id', on_delete=django.db.models.deletion.CASCADE,
                                        to='comics_db.ReadingList'),
            ),
        ])
    ]
