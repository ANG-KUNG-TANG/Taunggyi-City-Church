from django.http import JsonResponse
import logging
from jwt_backend import JWTBackend, TokenType

logger = logging.getLogger(__name__)

class JWTAuthMiddleware:
    """
    JWT Authentication Middleware for Django
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_backend = JWTBackend.get_instance()
        
        # Public paths that don't require authentication
        self.public_paths = [
            '/',
            '/admin/',
            '/static/',
            '/media/',
            '/favicon.ico',
            '/robots.txt',
            
            # TCC Auth endpoints
            '/tcc/auth/login/',
            '/tcc/auth/register/',
            '/tcc/auth/refresh/',
            '/tcc/auth/verify/',
            '/tcc/auth/forgot-password/',
            '/tcc/auth/reset-password/',
            '/tcc/auth/health/',
        ]
    
    def is_public_path(self, path: str) -> bool:
        """Check if path is public"""
        return any(path.startswith(public_path) for public_path in self.public_paths)
    
    def extract_token(self, request) -> str:
        """Extract JWT token from request"""
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # Check cookies as fallback
        return request.COOKIES.get('access_token', '')
    
    def __call__(self, request):
        # Check if path is public
        if self.is_public_path(request.path):
            return self.get_response(request)
        
        # Extract token
        token = self.extract_token(request)
        if not token:
            logger.warning(f"Authentication required but no token found: {request.path}")
            return JsonResponse(
                {
                    'error': 'Authentication required',
                    'message': 'Please provide a valid JWT token in Authorization header'
                },
                status=401
            )
        
        # Verify token
        try:
            # Import asyncio for async context
            import asyncio
            
            # Check if we're in async context
            if hasattr(request, '_sync_async_hack'):
                # In ASGI context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                is_valid, payload = loop.run_until_complete(
                    self.jwt_backend.verify_token(token, TokenType.ACCESS)
                )
                loop.close()
            else:
                # In WSGI context - use sync wrapper
                from asgiref.sync import async_to_sync
                is_valid, payload = async_to_sync(self.jwt_backend.verify_token)(
                    token, TokenType.ACCESS
                )
            
            if not is_valid:
                logger.warning(f"Invalid token for path: {request.path}")
                return JsonResponse(
                    {'error': 'Invalid or expired token'},
                    status=401
                )
            
            # Add user info to request
            request.user_id = payload.get('sub')
            request.user_email = payload.get('email')
            request.user_roles = payload.get('roles', [])
            request.jti = payload.get('jti')
            request.session_id = payload.get('session_id')
            
            logger.debug(f"Authenticated user {request.user_id} for {request.path}")
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return JsonResponse(
                {'error': 'Authentication failed'},
                status=401
            )
        
        return self.get_response(request)
