from .base import *

DEBUG = False

DATABASES = {
    'default': {
        'NAME': '<CONTRACT_SERVER_DB>',
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '<MYSQL_HOST>',
        'PORT': '<MYSQL_PORT>',
        'USER': '<MYSQL_USER>',
        'PASSWORD': '<MYSQL_PASSWORD>',
        'OPTIONS': {
            'autocommit': True,
        },
    }
}
