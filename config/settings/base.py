from logging import config
import os
from pathlib import Path
import environ
from datetime import timedelta

env = environ.Env(
    DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    SECURE_SSL_REDIRECT=(bool, False),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ──────────────────────────────
# Core
# ──────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")

# NEVER empty in prod → enforced in prod.py
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# ──────────────────────────────
# Apps
# ──────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "django_cleanup.apps.CleanupConfig",
    "corsheaders",
    "crispy_forms",
    "crispy_bootstrap5",
    'request_id',
    "apps.tcc",
]
AUTH_USER_MODEL = 'tcc.User'
MIDDLEWARE = [
    'config.middleware.RequestIDMiddleware',
    'config.middleware.GlobalExceptionMiddleware',
    'config.middleware.DatabaseQueryLoggingMiddleware',
    'config.middleware.SecurityHeadersMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ──────────────────────────────
# Templates
# ──────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ──────────────────────────────
# Database
# ──────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# ──────────────────────────────
# Auth & Password
# ──────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ──────────────────────────────
# Internationalization
# ──────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ──────────────────────────────
# Static & Media
# ──────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ──────────────────────────────
# REST Framework

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'apps.core.core_exceptions.handlers.django_handler.django_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {'anon': '100/day', 'user': '1000/day'}
}

# Enhanced JWT settings - FIXED: Use proper env calls
SIMPLE_JWT = {
    'SIGNING_KEY': env('JWT_SECRET'),
    'ALGORITHM': env('JWT_ALGORITHM', default='HS256'),
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_MINUTES', default=15)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_DAYS', default=7)),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ──────────────────────────────
# Cache (Redis / Async Ready)
# ──────────────────────────────
CACHE_BACKEND = env("CACHE_BACKEND", default="redis")
REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CACHE_DEFAULT_EXPIRE = env.int("CACHE_DEFAULT_EXPIRE", default=300)

if CACHE_BACKEND == "redis":
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": env.int("REDIS_MAX_CONNECTIONS", 50),
                    "encoding": "utf-8"
                },
                "SOCKET_CONNECT_TIMEOUT": env.int("REDIS_CONNECT_TIMEOUT", 5),
                "SOCKET_TIMEOUT": env.int("REDIS_SOCKET_TIMEOUT", 5),
                "RETRY_ON_TIMEOUT": True,
            },
            "TIMEOUT": CACHE_DEFAULT_EXPIRE,
        }
    }
    
    # Use cache for sessions when Redis is available
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
    
else:
    # fallback local memory cache (useful for development)
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
            "TIMEOUT": CACHE_DEFAULT_EXPIRE,
        }
    }
    
    # Use database for sessions when using locmem cache
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
    
# ──────────────────────────────
# CORS
# ──────────────────────────────
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL', default=False)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['X-Request-ID']
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# ──────────────────────────────
# Crispy Forms
# ──────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ──────────────────────────────
# Email
# ──────────────────────────────
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

# ──────────────────────────────
# Logging (Enhanced)
# ──────────────────────────────
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s","req":"%(request_id)s"}'
        },
        'detailed': {
            'format': '%(asctime)s %(levelname)s %(name)s [%(module)s:%(funcName)s] %(message)s req=%(request_id)s'
        }
    },
    'filters': {
        'request_id': {
            '()': 'config.middleware.RequestIDFilter'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
            'filters': ['request_id'],
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'app.log',
            'maxBytes': 10*1024*1024,
            'backupCount': 10,
            'formatter': 'structured',
            'filters': ['request_id'],
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'level': 'ERROR',
            'maxBytes': 10*1024*1024,
            'backupCount': 10,
            'formatter': 'detailed',
            'filters': ['request_id'],
        },
        'db_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'database.log',
            'level': 'INFO',
            'maxBytes': 10*1024*1024,
            'backupCount': 5,
            'formatter': 'structured',
            'filters': ['request_id'],
        },
    },
    'loggers': {
        'django': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
        'django.request': {'handlers': ['error_file'], 'level': 'ERROR', 'propagate': False},
        'django.db.backends': {'handlers': ['db_file'], 'level': 'INFO', 'propagate': False},
        'db': {'handlers': ['db_file', 'console'], 'level': 'INFO', 'propagate': False},
        'api': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}

# ──────────────────────────────
# Async and Event Loop Configuration
# ──────────────────────────────
ASYNC_MODE = env.bool('ASYNC_MODE', default=True)
ASYNC_DB_BACKEND = env.str('ASYNC_DB_BACKEND', default='aiomysql')
ASYNC_POOL_SIZE = env.int('ASYNC_POOL_SIZE', default=10)
ASYNC_TIMEOUT = env.int('ASYNC_TIMEOUT', default=30)

# ──────────────────────────────
# Snowflake ID Configuration
# ──────────────────────────────
SNOWFLAKE_DATACENTER_ID = env.int('SNOWFLAKE_DATACENTER_ID', default=1)
SNOWFLAKE_MACHINE_ID = env.int('SNOWFLAKE_MACHINE_ID', default=1)
SNOWFLAKE_EPOCH = env.int('SNOWFLAKE_EPOCH', default=1672531200000)

# ──────────────────────────────
# Application Constants
# ──────────────────────────────
MAX_FILE_UPLOAD_SIZE = env.int('MAX_FILE_UPLOAD_SIZE', default=10)
DEFAULT_PAGE_SIZE = env.int('DEFAULT_PAGE_SIZE', default=20)

# ──────────────────────────────
# Security Settings
# ──────────────────────────────
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=False)
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=False)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)
SECURE_BROWSER_XSS_FILTER = env.bool('SECURE_BROWSER_XSS_FILTER', default=True)
SECURE_CONTENT_TYPE_NOSNIFF = env.bool('SECURE_CONTENT_TYPE_NOSNIFF', default=True)
X_FRAME_OPTIONS = env('X_FRAME_OPTIONS', default='DENY')