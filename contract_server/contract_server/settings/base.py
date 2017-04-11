"""
Django settings for contract_server project.

Generated by 'django-admin startproject' using Django 1.10.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '+4hliv57!%_ue20+wl%**y%twqjov$!jon8d5qr+*8w-9l^agv'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

API_VERSION = "0.3.0"

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'oracles',
    'contracts',
    'evm_manager',
    'events',
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

ROOT_URLCONF = 'contract_server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'contract_server.wsgi.application'

STATIC_URL = '/static/'
CONTRACT_SERVER_API_URL = '<contract_server_url>'
OSS_API_URL = '<oss_url>'

GCOIN_BACKEND = 'gcoinbackend.backends.apibackend.GcoinAPIBackend'
GCOIN_BACKEND_SETTINGS = {
    'BASE_URL': OSS_API_URL,
    'KEY_STORE_CLASS': None
}

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
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

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/


# loggin related settings
LOG_DIR = BASE_DIR + '/../../log/'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_DIR + 'django.log',
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['file'],
            'propagate': False,
            'level': 'DEBUG',
        },
        'django.db.backends': {
            'handlers': ['file'],
            'propagate': False,
            'level': 'WARNING',
        },
        'django_crontab': {
            'handlers': ['file', 'mail_admins'],
            'level': 'DEBUG',
        },
        'contracts': {
            'handlers': ['file', 'mail_admins'],
            'level': 'DEBUG',
        },
        'oracles': {
            'handlers': ['file', 'mail_admins'],
            'level': 'DEBUG',
        },
        'contract_server': {
            'handlers': ['file', 'mail_admins'],
            'level': 'DEBUG',
        },
        'evm_manager': {
            'handlers': ['file', 'mail_admins'],
            'level': 'DEBUG',
        },
        'events': {
            'handlers': ['file', 'mail_admins'],
            'level': 'DEBUG',
        }
    }
}