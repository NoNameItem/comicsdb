"""
Template for secure parameters which have no place in employeeSource control, like sensitive or installation-specific
settings.
To deploy set the values and rename file to custom_settings.py
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "1"  # You realy need to change this
DEBUG = True
ALLOWED_HOSTS = None
DATABASES = {'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '',
    }}
LANGUAGE_CODE = "en-us"
TIME_ZONE = 'UTC'

EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = os.path.join(BASE_DIR, '')

# Common DO settings
DO_KEY_ID = "R7HWT7TAPZ67BCA5672C"
DO_SECRET_ACCESS_KEY = "2agkIbN3IcDlf1fX0U+Y6DWHSuu6zxKMKuXbHsVltZo"
DO_STORAGE_BUCKET_NAME = "comicsdb"
DO_REGION_NAME = "ams3"
DO_ENDPOINT_URL = 'https://ams3.digitaloceanspaces.com/'
DO_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
DO_PUBLIC_URL = "https://comicsdb.ams3.cdn.digitaloceanspaces.com"

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = os.path.join(BASE_DIR, '')
MEDIA_URL = ""
