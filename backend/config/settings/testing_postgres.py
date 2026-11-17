from .base import *

DEBUG = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Retain the PostgreSQL DATABASES configuration inherited from base.py.
# Do not override PASSWORD_HASHERS.
