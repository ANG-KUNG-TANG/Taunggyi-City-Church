from django.utils.deprecation import MiddlewareMixin

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Middleware to add security headers to responses"""
    
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
    
    def process_response(self, request, response):
        """Add security headers to response"""
        for header, value in self.headers.items():
            response[header] = value
        return response