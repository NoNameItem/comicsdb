"""
Template for secure parameters which have no place in employeeSource control, like sensitive or installation-specific settings
To deploy set the values and rename file to custom_settings.py
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "oracle"
DEBUG = True
ALLOWED_HOSTS = None
DATABASES = {'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mydatabase',
    }}
LANGUAGE_CODE = "en-us"
TIME_ZONE = 'UTC'
