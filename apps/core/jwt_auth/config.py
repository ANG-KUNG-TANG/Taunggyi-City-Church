from django.conf import settings

class JWTConfig:
    # Secrets
    ACCESS_SECRET = getattr(settings, 'JWT_ACCESS_SECRET', settings.SECRET_KEY)
    REFRESH_SECRET = getattr(settings, 'JWT_REFRESH_SECRET', settings.SECRET_KEY + '_refresh')
    
    # Expiration (in seconds)
    ACCESS_TOKEN_LIFETIME = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', 15 * 60)  # 15 min
    REFRESH_TOKEN_LIFETIME = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', 7 * 24 * 60 * 60)  # 7 days
    
    # Algorithm
    ALGORITHM = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    
    # Issuer and Audience
    ISSUER = getattr(settings, 'JWT_ISSUER', 'your-app')
    AUDIENCE = getattr(settings, 'JWT_AUDIENCE', 'your-app-users')