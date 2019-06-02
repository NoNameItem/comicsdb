"""
Django settings for comicsdb project.

Generated by 'django-admin startproject' using Django 2.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

from comicsdb import custom_settings

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = custom_settings.BASE_URL

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = custom_settings.SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = custom_settings.DEBUG

ALLOWED_HOSTS = custom_settings.ALLOWED_HOSTS

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_s3_storage',
    'rest_framework',
    'django_filters',
    'crispy_forms',
    'drf_yasg',
    'registration',
    'knox',
    'django_celery_beat',
    'el_pagination',
    'anymail',
    'comics_db',
    'django_cleanup.apps.CleanupConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'comicsdb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',  # For EL-pagination
            ],
        },
    },
]


WSGI_APPLICATION = 'comicsdb.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = custom_settings.DATABASES

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = custom_settings.LANGUAGE_CODE

TIME_ZONE = custom_settings.TIME_ZONE

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Common DO settings

DO_KEY_ID = custom_settings.DO_KEY_ID
DO_SECRET_ACCESS_KEY = custom_settings.DO_SECRET_ACCESS_KEY
DO_STORAGE_BUCKET_NAME = custom_settings.DO_STORAGE_BUCKET_NAME
DO_REGION_NAME = custom_settings.DO_REGION_NAME
DO_ENDPOINT_URL = custom_settings.DO_ENDPOINT_URL
DO_OBJECT_PARAMETERS = custom_settings.DO_OBJECT_PARAMETERS
DO_PUBLIC_URL = custom_settings.DO_PUBLIC_URL

# django-s3-storage common settings

AWS_REGION = custom_settings.DO_REGION_NAME
AWS_ACCESS_KEY_ID = custom_settings.DO_KEY_ID
AWS_SECRET_ACCESS_KEY = custom_settings.DO_SECRET_ACCESS_KEY

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'static_root')

# STATICFILES_STORAGE = custom_settings.STATICFILES_STORAGE
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# django-s3-storage static settings

AWS_S3_ENDPOINT_URL_STATIC = custom_settings.DO_ENDPOINT_URL_STATIC
AWS_S3_BUCKET_NAME_STATIC = custom_settings.DO_STORAGE_BUCKET_NAME_STATIC
AWS_S3_KEY_PREFIX_STATIC = "static"
AWS_S3_PUBLIC_URL_STATIC = custom_settings.DO_PUBLIC_URL_STATIC + '/static/'
AWS_S3_FILE_OVERWRITE_STATIC = True

# Media settings
# https://docs.djangoproject.com/en/2.1/topics/files/

DEFAULT_FILE_STORAGE = custom_settings.DEFAULT_FILE_STORAGE
MEDIA_ROOT = custom_settings.MEDIA_ROOT
MEDIA_URL = custom_settings.MEDIA_URL

# django-s3-storage file storage settings

AWS_S3_ENDPOINT_URL = custom_settings.DO_ENDPOINT_URL
AWS_S3_BUCKET_NAME = custom_settings.DO_STORAGE_BUCKET_NAME_MEDIA
AWS_S3_KEY_PREFIX = "media"
AWS_S3_PUBLIC_URL = custom_settings.DO_PUBLIC_URL_MEDIA + '/media/'
AWS_S3_FILE_OVERWRITE = False
AWS_S3_BUCKET_AUTH = False

# Email
# https://docs.djangoproject.com/en/2.1/topics/email/
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

# DRF Global Settings
REST_FRAMEWORK = {
    'URL_FIELD_NAME': "detail_url",
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'knox.auth.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'comics_db.throttling.AllowAdminThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '3000/day'
    }
}
REST_KNOX = {
    'TOKEN_TTL': None
}

# Django Registration Redux Settins
# https://django-registration-redux.readthedocs.io

REGISTRATION_DEFAULT_FROM_EMAIL = "register@comicsdb.nonameitem.com"
REGISTRATION_AUTO_LOGIN = True
LOGIN_REDIRECT_URL = "site-main"
LOGOUT_REDIRECT_URL = "site-main"
ACCOUNT_ACTIVATION_DAYS = 30
LOGIN_URL = "/accounts/login"

# Celery settings
CELERY_BROKER_URL = custom_settings.CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Marvel API settings
MARVEL_PUBLIC_KEY = custom_settings.MARVEL_PUBLIC_KEY
MARVEL_PRIVATE_KEY = custom_settings.MARVEL_PRIVATE_KEY

# Endless Pagination Settings
EL_PAGINATION_PER_PAGE = 20
EL_PAGINATION_ORPHANS = 3

# Anymail settings
ANYMAIL = custom_settings.ANYMAIL
DEFAULT_FROM_EMAIL = 'noreply@comicsdb.nonameitem.com'