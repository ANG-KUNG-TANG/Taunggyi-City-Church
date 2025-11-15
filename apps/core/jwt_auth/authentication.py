from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from .utils.header_parser import extract_bearer_token
from .service.token_service import TokenService
from .exceptions import JWTException

class JWTAuthentication(authentication.BaseAuthentication):
    """
    DRF Authentication class using JWT tokens
    """
    
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        token = extract_bearer_token(auth_header)
        
        if not token:
            return None
        
        try:
            payload = TokenService.validate_access_token(token)
            
            # Get user from database
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(id=payload.user_id)
            except User.DoesNotExist:
                raise AuthenticationFailed('User not found')
            
            return (user, payload)
            
        except JWTException as e:
            raise AuthenticationFailed(str(e))