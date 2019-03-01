"""
Template for secure parameters which have no place in employeeSource control, like sensitive or installation-specific settings
To deploy set the values and rename file to custom_settings.py
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "1" # You realy need to change this
DEBUG = True
ALLOWED_HOSTS = None
DATABASES = {'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mydatabase',
    }}
LANGUAGE_CODE = "en-us"
TIME_ZONE = 'UTC'

EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = os.path.join(BASE_DIR, '/tmp/app-messages')

# DO Cloud setup
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_STORAGE_BUCKET_NAME = ""
AWS_S3_REGION_NAME = ""
AWS_S3_ENDPOINT_URL = ''
AWS_S3_OBJECT_PARAMETERS = {}
