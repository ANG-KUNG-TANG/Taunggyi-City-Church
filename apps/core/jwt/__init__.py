import logging
from django.conf import settings
from .jwt_backend import JWTBackend, TokenConfig

logger = logging.getLogger(__name__)

_jwt_backend = None

def get_jwt_backend():
    """Get or initialize JWT backend singleton"""
    global _jwt_backend
    if _jwt_backend is None:
        try:
            # Check if JWT_CONFIG exists in settings
            if not hasattr(settings, 'JWT_CONFIG'):
                # Create default config
                jwt_config = {
                    'ACCESS_TOKEN_EXPIRY': 900,
                    'REFRESH_TOKEN_EXPIRY': 604800,
                    'RESET_TOKEN_EXPIRY': 1800,
                    'ALGORITHM': 'RS256',
                    'ISSUER': 'auth-service',
                    'AUDIENCE': ['api'],
                }
            else:
                jwt_config = settings.JWT_CONFIG
            
            # Create token config
            config = TokenConfig(
                access_token_expiry=jwt_config['ACCESS_TOKEN_EXPIRY'],
                refresh_token_expiry=jwt_config['REFRESH_TOKEN_EXPIRY'],
                reset_token_expiry=jwt_config['RESET_TOKEN_EXPIRY'],
                algorithm=jwt_config['ALGORITHM'],
                issuer=jwt_config['ISSUER'],
                audience=jwt_config['AUDIENCE']
            )
            
            # Initialize with cache
            from ..cache.async_cache import get_cache_client
            cache = get_cache_client()
            
            _jwt_backend = JWTBackend.get_instance(cache=cache, config=config)
            logger.info("JWT Backend initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize JWT backend: {e}")
            # Create fallback without cache
            _jwt_backend = JWTBackend.get_instance(config=config)
    
    return _jwt_backend