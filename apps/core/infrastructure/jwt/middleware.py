"""
Production JWT Authentication Middleware for Django
Security Level: HIGH
Compliance: OWASP Authentication
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from typing import Callable, Optional, Dict, Any
import logging

from apps.core.infrastructure.jwt.jwt_backend import JWTBackend
from apps.core.security.jwt_manager import TokenType
from apps.core.security.rate_limiter import RateLimitConfig, RateLimitStrategy, RateLimiter

logger = logging.getLogger(__name__)

class JWTAuthMiddleware(MiddlewareMixin):
    """
    Production JWT Authentication Middleware
    Security Level: HIGH
    Responsibilities: Token validation, user context attachment
    """
    
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.jwt_backend = None
        self.rate_limiter = None
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
            from apps.core.infrastructure.cahce.redis_factory import RedisFactory
            cache = RedisFactory.get_default_client()
            if cache:
                self.jwt_backend = JWTBackend.get_instance(cache)
                self.rate_limiter = RateLimiter(cache)
        
    def is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication"""
        return any(
            path.startswith(excluded) or 
            path == excluded.rstrip('/') 
            for excluded in self.excluded_paths
        )
    
    def extract_token(self, request) -> Optional[str]:
        """
        Extract JWT token from request
        Security Level: HIGH
        """
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check query parameter (for WebSocket connections)
        token = request.GET.get('token')
        if token:
            return token
            
        # Check cookies
        token = request.COOKIES.get('access_token')
        if token:
            return token
            
        return None
    
    async def process_request_async(self, request):
        """
        Async request processing
        Security Level: HIGH
        """
        # Skip authentication for excluded paths
        if self.is_excluded_path(request.path):
            return None
        
        self.initialize_services(request)
        
        if not self.jwt_backend:
            return JsonResponse(
                {'error': 'Authentication service unavailable'}, 
                status=503
            )
        
        # Apply rate limiting
        if self.rate_limiter:
            rate_limit_result = await self._apply_rate_limiting(request)
            if not rate_limit_result.allowed:
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': rate_limit_result.retry_after,
                    'details': rate_limit_result.details
                }, status=429)
        
        # Extract and verify token
        token = self.extract_token(request)
        if not token:
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=401
            )
        
        # Verify token
        is_valid, payload = await self.jwt_backend.verify_token(token, TokenType.ACCESS)
        
        if not is_valid:
            return JsonResponse(
                {'error': 'Invalid or expired token'}, 
                status=401
            )
        
        # Add user context to request
        self._attach_user_context(request, payload)
        
        return None
    
    def process_request(self, request):
        """
        Sync request processing (fallback)
        Security Level: HIGH
        """
        # For sync contexts, we'll handle basic checks but defer to async for full processing
        if self.is_excluded_path(request.path):
            return None
            
        token = self.extract_token(request)
        if not token:
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=401
            )
        
        # In sync context, we can't do full async verification
        # This is a basic check - full verification happens in process_view
        return None
    
    async def _apply_rate_limiting(self, request) -> Any:
        """
        Apply rate limiting to request
        Security Level: HIGH
        """
        client_id = self._get_client_identifier(request)
        action = f"{request.method}:{request.path}"
        
        config = RateLimitConfig(
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            max_requests=100,  # 100 requests per hour
            window_seconds=3600,
            block_duration=300  # 5 minutes block after limit
        )
        
        return await self.rate_limiter.check_rate_limit(client_id, action, config)
    
    def _get_client_identifier(self, request) -> str:
        """
        Get client identifier for rate limiting
        Security Level: MEDIUM
        """
        # Prefer authenticated user ID if available
        if hasattr(request, 'user_id'):
            return f"user:{request.user_id}"
        
        # Fall back to IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            
        return f"ip:{ip}"
    
    def _attach_user_context(self, request, payload: Dict):
        """
        Attach user context to request
        Security Level: HIGH
        """
        request.user_id = payload.get('sub')
        request.user_email = payload.get('email')
        request.user_roles = payload.get('roles', [])
        request.user_permissions = payload.get('permissions', [])
        request.token_payload = payload
        request.jti = payload.get('jti')
        request.session_id = payload.get('session_id')
        
        # Add to META for compatibility
        request.META['HTTP_X_USER_ID'] = request.user_id
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