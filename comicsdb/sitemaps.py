from django.contrib.sitemaps import GenericSitemap

from comics_db import models


publisher_info = {
    'queryset': models.Publisher.objects.all(),
    'date_field': 'modified_dt'
}

universe_info = {
    'queryset': models.Universe.objects.all(),
    'date_field': 'modified_dt'
}

title_info = {
    'queryset': models.Title.objects.all(),
    'date_field': 'modified_dt'
}

issue_info = {
    'queryset': models.Issue.objects.all(),
    'date_field': 'modified_dt'
}

sitemaps = {
    'publishers': GenericSitemap(publisher_info, priority=0.1),
    'universes': GenericSitemap(universe_info, priority=0.1),
    'titles': GenericSitemap(title_info, priority=0.5),
    'issues': GenericSitemap(issue_info, priority=1.0)
}