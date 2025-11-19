import os
from datetime import timedelta

"""
Security Configuration
Use this for custom security settings not covered by Django's built-in security
"""

# Rate Limiting Configuration
RATE_LIMIT_CONFIGS = {
    'login': {
        'max_requests': int(os.getenv('RATE_LIMIT_LOGIN_ATTEMPTS', 5)),
        'window_seconds': 300,  # 5 minutes
        'strategy': 'sliding_window'
    },
    'api': {
        'max_requests': int(os.getenv('RATE_LIMIT_API_REQUESTS', 1000)),
        'window_seconds': 3600,  # 1 hour
        'strategy': 'sliding_window'
    },
    'password_reset': {
        'max_requests': int(os.getenv('RATE_LIMIT_TOKEN_REFRESH', 10)),
        'window_seconds': 900,  # 15 minutes
        'strategy': 'sliding_window'
    }
}

# Password Security
BCRYPT_ROUNDS = int(os.getenv('BCRYPT_ROUNDS', 12))
MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
LOGIN_TIMEOUT_MINUTES = int(os.getenv('LOGIN_TIMEOUT_MINUTES', 15))

# Security Headers (complementary to base.py)
SECURITY_HEADERS = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin'
}

# Key Rotation
KEY_ROTATION_INTERVAL = int(os.getenv('KEY_ROTATION_INTERVAL', 86400))  # 24 hours