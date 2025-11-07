from .base import *

DEBUG = False

# ──────────────────────────────
# Production Security Settings
# ──────────────────────────────
# HSTS Settings (enable in production)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=True)

# SSL Settings (enable in production)
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)

# Other Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ──────────────────────────────
# Production Allowed Hosts
# ──────────────────────────────
# This should be set via environment variable in production
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['your-production-domain.com'])

# ──────────────────────────────
# Production CORS
# ──────────────────────────────
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# ──────────────────────────────
# Production Logging
# ──────────────────────────────
# Less verbose logging in production
LOGGING['loggers']['django.db.backends']['level'] = 'ERROR'
LOGGING['loggers']['django']['level'] = 'INFO'
LOGGING['loggers']['api']['level'] = 'INFO'

# ──────────────────────────────
# Production REST Framework
# ──────────────────────────────
# JSON only in production
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
)

# Strict permissions in production
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.IsAuthenticated'
]

# Enable throttling in production
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/day', 
    'user': '1000/day'
}

print("🔒 Production mode: All security features enabled")