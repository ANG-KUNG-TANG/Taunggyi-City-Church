from django.http import JsonResponse
import logging
import asyncio

logger = logging.getLogger(__name__)

class JWTAuthMiddleware:
    """
    JWT Authentication Middleware - Fixed for TCC URL structure
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_backend = None
        
        # Updated excluded paths for TCC URL structure
        self.excluded_paths = [
            '/',                    # Root URL
            '/admin/',              # Django admin
            '/static/',             # Static files
            '/media/',              # Media files
            '/favicon.ico',         # Favicon
            '/robots.txt',          # Robots.txt
            
            # TCC Auth endpoints - note the /tcc/ prefix
            '/tcc/auth/login/',
            '/tcc/auth/register/',
            '/tcc/auth/refresh/',
            '/tcc/auth/verify/',
            '/tcc/auth/forgot-password/',
            '/tcc/auth/reset-password/',
            
            # Add other public TCC endpoints if needed
        ]
    
    def initialize_jwt_backend(self):
        """Initialize JWT backend"""
        if self.jwt_backend is None:
            try:
                from apps.core.jwt import get_jwt_backend
                self.jwt_backend = get_jwt_backend()
                logger.info("JWT Backend initialized in middleware")
            except ImportError as e:
                logger.warning(f"JWT backend not available: {e}")
                self.jwt_backend = None
            except Exception as e:
                logger.error(f"Failed to initialize JWT backend: {e}")
                self.jwt_backend = None
    
    def is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication"""
        # Normalize path for comparison
        normalized_path = path.rstrip('/') if path != '/' else path
        
        for excluded in self.excluded_paths:
            excluded_normalized = excluded.rstrip('/') if excluded != '/' else excluded
            
            # Exact match
            if normalized_path == excluded_normalized:
                return True
            
            # Path starts with excluded path
            if path.startswith(excluded):
                return True
        
        return False
    
    def extract_token(self, request) -> str:
        """Extract JWT token from request"""
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # Check cookies
        return request.COOKIES.get('access_token', '')
    
    def _attach_user_context(self, request, payload: dict):
        """Attach user context to request"""
        request.user_id = payload.get('sub')
        request.user_email = payload.get('email')
        request.user_roles = payload.get('roles', [])
        request.user_permissions = payload.get('permissions', [])
        request.jti = payload.get('jti')
        request.session_id = payload.get('session_id')
        
        # For Django auth compatibility
        if hasattr(request, 'user') and request.user.is_anonymous:
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
    
    def __call__(self, request):
        """Main middleware entry point"""
        # Check if path is excluded
        if self.is_excluded_path(request.path):
            logger.debug(f"Path {request.path} is excluded from JWT auth")
            return self.get_response(request)
            
        self.initialize_jwt_backend()
        
        # If JWT backend isn't available, allow access but log warning
        if not self.jwt_backend:
            logger.warning(f"JWT backend not available for path: {request.path}")
            return self.get_response(request)
        
        # Extract token
        token = self.extract_token(request)
        if not token:
            logger.warning(f"No token found for protected path: {request.path}")
            return JsonResponse(
                {
                    'error': 'Authentication required', 
                    'path': request.path,
                    'message': 'Please include a valid JWT token in Authorization header'
                }, 
                status=401
            )
        
        # Verify token
        try:
            # Run async verification in sync context
            if hasattr(asyncio, 'run'):
                is_valid, payload = asyncio.run(self.jwt_backend.verify_token(token))
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                is_valid, payload = loop.run_until_complete(self.jwt_backend.verify_token(token))
                loop.close()
                
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return JsonResponse(
                {'error': 'Token verification failed'}, 
                status=401
            )
        
        if not is_valid:
            return JsonResponse(
                {'error': 'Invalid or expired token'}, 
                status=401
            )
        
        # Add user context to request
        self._attach_user_context(request, payload)
        logger.debug(f"JWT authentication successful for user {request.user_id} on path {request.path}")
        
        # Continue with the request
        return self.get_response(request)