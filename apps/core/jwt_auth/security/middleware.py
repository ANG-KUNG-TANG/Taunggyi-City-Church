# core/security/middleware.py
from django.utils.deprecation import MiddlewareMixin

from apps.core.jwt_auth.security import jwt_manager

class JWTMiddleware(MiddlewareMixin):
    def process_request(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Bearer "):
            request.jwt_payload = None
            return None
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = jwt_manager.validate_access_token(token)
            request.jwt_payload = payload
        except Exception:
            request.jwt_payload = None
        return None
