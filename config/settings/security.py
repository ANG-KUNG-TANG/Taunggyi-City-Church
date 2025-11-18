import os
from datetime import timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# JWT Configuration
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'RS256')
JWT_ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
JWT_REFRESH_TOKEN_LIFETIME = timedelta(days=7)
JWT_LEEWAY = timedelta(seconds=10)
JWT_ISSUER = os.getenv('JWT_ISSUER', 'your-production-app')
JWT_AUDIENCE = os.getenv('JWT_AUDIENCE', 'your-app-users')

# RSA Key Configuration (for RS256)
JWT_PRIVATE_KEY = os.getenv('JWT_PRIVATE_KEY')
JWT_PUBLIC_KEY = os.getenv('JWT_PUBLIC_KEY')

# Redis Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-cluster.production.com')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
REDIS_MAX_CONNECTIONS = int(os.getenv('REDIS_MAX_CONNECTIONS', 50))

# Rate Limiting
RATE_LIMIT_LOGIN_ATTEMPTS = 5  # per minute
RATE_LIMIT_API_REQUESTS = 1000  # per hour
RATE_LIMIT_TOKEN_REFRESH = 10  # per minute

# Security Headers
SECURITY_HEADERS = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin'
}

def generate_rsa_key_pair():
    """Generate RSA key pair for JWT signing"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem.decode('utf-8'), public_pem.decode('utf-8')

"""
Production Security Configuration
Security Level: CRITICAL
"""
import os
from datetime import timedelta
from typing import List

# JWT Configuration
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'RS256')
JWT_ACCESS_EXPIRY = int(os.getenv('JWT_ACCESS_EXPIRY', 900))  # 15 minutes
JWT_REFRESH_EXPIRY = int(os.getenv('JWT_REFRESH_EXPIRY', 604800))  # 7 days
JWT_RESET_EXPIRY = int(os.getenv('JWT_RESET_EXPIRY', 1800))  # 30 minutes
JWT_ISSUER = os.getenv('JWT_ISSUER', 'auth-service')
JWT_AUDIENCE = os.getenv('JWT_AUDIENCE', 'api').split(',')
JWT_LEEWAY_SECONDS = int(os.getenv('JWT_LEEWAY_SECONDS', 30))

# Security Settings
BCRYPT_ROUNDS = int(os.getenv('BCRYPT_ROUNDS', 12))
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
LOGIN_TIMEOUT_MINUTES = int(os.getenv('LOGIN_TIMEOUT_MINUTES', 15))

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') 
    if origin.strip()
]

# Security Headers
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Referrer-Policy': 'strict-origin-when-cross-origin'
}

# Key Rotation
KEY_ROTATION_INTERVAL = int(os.getenv('KEY_ROTATION_INTERVAL', 86400))  # 24 hours
KEY_CACHE_EXPIRY = int(os.getenv('KEY_CACHE_EXPIRY', 172800))  # 48 hours

# Rate Limiting
RATE_LIMIT_CONFIGS = {
    'login': {
        'max_requests': 5,
        'window_seconds': 300,  # 5 minutes
        'strategy': 'sliding_window'
    },
    'api': {
        'max_requests': 100,
        'window_seconds': 3600,  # 1 hour
        'strategy': 'sliding_window'
    },
    'password_reset': {
        'max_requests': 3,
        'window_seconds': 900,  # 15 minutes
        'strategy': 'sliding_window'
    }
}