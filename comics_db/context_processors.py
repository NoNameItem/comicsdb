from django.conf import settings as django_settings


def settings(request):
    return {'django_settings': django_settings}