from .base import *

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0", "192.168.1.*"]

# ──────────────────────────────
# Development Security Settings
# ──────────────────────────────
# Disable security features for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# ──────────────────────────────
# Debug Toolbar
# ──────────────────────────────
try:
    import debug_toolbar
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
    
    # Debug toolbar configuration
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: True,
    }
except ImportError:
    print("⚠ debug_toolbar not installed, skipping...")

# ──────────────────────────────
# Development Email
# ──────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ──────────────────────────────
# Development CORS
# ──────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ──────────────────────────────
# Development Logging
# ──────────────────────────────
LOGGING['loggers']['django.db.backends']['level'] = 'DEBUG'
LOGGING['loggers']['django.db.backends']['handlers'].append('console')

# More verbose logging for development
LOGGING['loggers']['django']['level'] = 'INFO'
LOGGING['loggers']['api']['level'] = 'DEBUG'

# ──────────────────────────────
# Development REST Framework
# ──────────────────────────────
# Browsable API in development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

# No throttling in development
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {'anon': None, 'user': None}

# More permissive permissions in development
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.AllowAny'
]

# ──────────────────────────────
# Development-specific Settings
# ──────────────────────────────
# Show emails in console
if 'mail' in EMAIL_BACKEND:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable password validation in development for easier testing
AUTH_PASSWORD_VALIDATORS = []

# Print security status
print("🔓 Development mode: Security features disabled for local development")