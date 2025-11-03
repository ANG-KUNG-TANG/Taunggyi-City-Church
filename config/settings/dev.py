from .base import *

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0", "192.168.1.*"]

# Debug Toolbar
try:
    import debug_toolbar
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# Dev Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Dev CORS
CORS_ALLOW_ALL_ORIGINS = True

# Dev Logging
LOGGING['loggers']['django.db.backends']['level'] = 'DEBUG'
LOGGING['loggers']['django.db.backends']['handlers'].append('console')

# Browsable API (FIXED)
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += (
    'rest_framework.renderers.BrowsableAPIRenderer',
)

# No throttling
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {'anon': None, 'user': None}