"""
Production JWT Authentication Middleware for Django
Security Level: HIGH
Compliance: OWASP Authentication
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from typing import Callable, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class JWTAuthMiddleware(MiddlewareMixin):
    """
    Production JWT Authentication Middleware
    Security Level: HIGH
    """
    
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.jwt_backend = None
        self.excluded_paths = [
            '/auth/login/',
            '/auth/register/',
            '/auth/token/refresh/',
            '/health/',
            '/docs/',
            '/admin/',
            '/static/',
            '/media/'
        ]
        
    def initialize_services(self, request):
        """Lazy initialization of services"""
        if self.jwt_backend is None:
            try:
                from apps.core.infrastructure.jwt.jwt_backend import JWTBackend
                # Initialize without cache for now
                self.jwt_backend = JWTBackend.get_instance()
            except ImportError as e:
                logger.error(f"Failed to initialize JWTBackend: {e}")
                self.jwt_backend = None
        
    def is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication"""
        return any(
            path.startswith(excluded) or 
            path == excluded.rstrip('/') 
            for excluded in self.excluded_paths
        )
    
    def extract_token(self, request) -> Optional[str]:
        """Extract JWT token from request"""
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # Check query parameter
        token = request.GET.get('token')
        if token:
            return token
            
        # Check cookies
        token = request.COOKIES.get('access_token')
        if token:
            return token
            
        return None
    
    async def process_request_async(self, request):
        """Async request processing"""
        if self.is_excluded_path(request.path):
            return None
        
        self.initialize_services(request)
        
        if not self.jwt_backend:
            return JsonResponse(
                {'error': 'Authentication service unavailable'}, 
                status=503
            )
        
        # Extract and verify token
        token = self.extract_token(request)
        if not token:
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=401
            )
        
        # Verify token
        try:
            is_valid, payload = await self.jwt_backend.verify_token(token)
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
        
        return None
    
    def process_request(self, request):
        """Sync request processing"""
        if self.is_excluded_path(request.path):
            return None
            
        token = self.extract_token(request)
        if not token:
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=401
            )
        
        return None
    
    def _attach_user_context(self, request, payload: Dict):
        """Attach user context to request"""
        request.user_id = payload.get('sub')
        request.user_email = payload.get('email')
        request.user_roles = payload.get('roles', [])
        request.user_permissions = payload.get('permissions', [])
        request.token_payload = payload
        request.jti = payload.get('jti')
        request.session_id = payload.get('session_id')
        
        # Add to META for compatibility
        request.META['HTTP_X_USER_ID'] = request.user_id or ''
        request.META['HTTP_X_USER_EMAIL'] = request.user_email or ''

    def process_response(self, request, response):
        """
        Process outgoing response
        Security Level: MEDIUM
        """
        # Add security headers
        response = self._add_security_headers(response)
        
        # Add user context to response headers for debugging
        if hasattr(request, 'user_id'):
            response['X-User-ID'] = request.user_id
            response['X-User-Roles'] = ','.join(request.user_roles)
        
        # Add rate limit info if available
        if hasattr(request, 'rate_limit_info'):
            info = request.rate_limit_info
            response['X-RateLimit-Limit'] = str(info.get('limit', 100))
            response['X-RateLimit-Remaining'] = str(info.get('remaining', 100))
            response['X-RateLimit-Reset'] = str(info.get('reset_time', 0))
        
        return response
    
    def _add_security_headers(self, response):
        """
        Add security headers to response
        Security Level: HIGH
        """
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
        
        for header, value in security_headers.items():
            if header not in response:
                response[header] = value
                
        return response
    
    async def __call__(self, request):
        """
        Async middleware support
        Security Level: HIGH
        """
        # Process request
        response = await self.process_request_async(request)
        if response is not None:
            return response
        
        # Get response
        response = await self.get_response(request)
        
        # Process response
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        
        return response

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Dedicated Security Headers Middleware
    Security Level: HIGH
    """
    
    def process_response(self, request, response):
        """
        Add security headers to all responses
        Security Level: HIGH
        """
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'",
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
            'Cache-Control': 'no-store, no-cache, must-revalidate'
        }
        
        for header, value in headers.items():
            response[header] = value
            
        return response