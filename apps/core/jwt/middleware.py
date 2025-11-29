from .rate_limiter import *
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
            '/auth/token/verify/',
            '/health/',
            '/docs/',
            '/admin/',
            '/static/',
            '/media/',
            '/api/auth/',
        ]
    
    def initialize_jwt_backend(self):
        """Initialize JWT backend"""
        if self.jwt_backend is None:
            try:
                from apps.core.jwt import get_jwt_backend
                self.jwt_backend = get_jwt_backend()
                logger.info("JWT Backend initialized in middleware")
            except Exception as e:
                logger.error(f"Failed to initialize JWT backend: {e}")
                self.jwt_backend = None
    
    def is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication"""
        return any(
            path.startswith(excluded) or 
            path == excluded.rstrip('/') 
            for excluded in self.excluded_paths
        )
    
    def extract_token(self, request) -> str:
        """Extract JWT token from request"""
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # Check cookies
        return request.COOKIES.get('access_token')
    
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
    
    def process_request(self, request):
        """Sync request processing"""
        if self.is_excluded_path(request.path):
            return None
            
        self.initialize_jwt_backend()
        
        if not self.jwt_backend:
            return JsonResponse(
                {'error': 'Authentication service unavailable'}, 
                status=503
            )
        
        # Extract token
        token = self.extract_token(request)
        if not token:
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=401
            )
        
        # Verify token using sync wrapper
        try:
            import asyncio
            
            # Check if we're in async context
            try:
                # Try to get running loop (async context)
                loop = asyncio.get_running_loop()
                # We're in async context, use different approach
                async def verify():
                    return await self.jwt_backend.verify_token(token)
                
                # This is simplified - in real async context, handle differently
                is_valid, payload = asyncio.run(verify())
            except RuntimeError:
                # No running loop (sync context)
                if hasattr(asyncio, 'run'):
                    # Python 3.7+
                    is_valid, payload = asyncio.run(self.jwt_backend.verify_token(token))
                else:
                    # Python 3.6 compatibility
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
        return None

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Security headers middleware"""
    
    def process_response(self, request, response):
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'",
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        }
        
        for header, value in headers.items():
            if header not in response:
                response[header] = value
                
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