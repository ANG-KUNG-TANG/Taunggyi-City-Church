# config/settings/prod.py
from .base import *
from django.core.exceptions import ImproperlyConfigured

DEBUG = False

# CRITICAL: Enforce ALLOWED_HOSTS
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in production!")

# Security
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

MIDDLEWARE.insert(1, 'config.middleware.SecurityHeadersMiddleware')

# Production DB
DATABASES['default']['CONN_MAX_AGE'] = 300

# Production Logging
LOGGING['handlers']['console']['formatter'] = 'structured'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['django.db.backends']['level'] = 'WARNING'

# Email
ADMINS = [('Admin', env('ADMIN_EMAIL'))]
SERVER_EMAIL = DEFAULT_FROM_EMAIL