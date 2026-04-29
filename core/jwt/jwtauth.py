"""
DRF-Compatible JWT Authentication Class
FIXED: Includes proper role and permission handling
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import logging
import re
import jwt as pyjwt
from django.conf import settings

from core.jwt.jwt_backend import JWTBackend, TokenType

logger = logging.getLogger(__name__)


class JWTAuthentication(BaseAuthentication):
    """
    Token-based authentication using JWT.
    
    Clients should authenticate by passing the token in the Authorization HTTP header:
    Authorization: Bearer <token>
    """
    
    keyword = 'Bearer'
    
    def __init__(self):
        super().__init__()
        self.jwt_backend = JWTBackend.get_instance()
        logger.debug("JWTAuthentication initialized")
    
    def authenticate(self, request):
        """
        Authenticate the request and return (user, token) tuple.
        Returns None if no token found (allows other authenticators to try).
        """
        # Extract token from request
        token = self.extract_token(request)
        
        if token is None:
            logger.debug("No token found in request")
            return None
        
        # Validate token format before attempting verification
        if not self.is_valid_jwt_format(token):
            logger.error(f"Invalid JWT format. Token length: {len(token)}")
            logger.error(f"Token preview: '{token[:100] if len(token) > 100 else token}'")
            raise AuthenticationFailed('Invalid token format')
        
        logger.debug(f"Token extracted, length: {len(token)}")
        
        try:
            # Use the backend's verification method directly
            is_valid, payload = self.jwt_backend.verify_token_sync(token, TokenType.ACCESS)
            
            if not is_valid or not payload:
                logger.warning("Token verification failed")
                raise AuthenticationFailed('Invalid or expired token')
            
            # Ensure 'sub' is string
            if 'sub' in payload and not isinstance(payload['sub'], str):
                payload['sub'] = str(payload['sub'])
            
            # Backward compatibility: Ensure role and permission fields exist
            if 'role' not in payload:
                payload['role'] = payload.get('roles', ['member'])[0]
            if 'is_superuser' not in payload:
                payload['is_superuser'] = payload.get('role') in ['super_admin', 'admin']
            if 'is_staff' not in payload:
                payload['is_staff'] = payload.get('role') in ['super_admin', 'admin', 'staff']
            
            logger.info(f"Token verified for user: {payload.get('email')} "
                       f"with role: {payload.get('role')}, "
                       f"is_superuser: {payload.get('is_superuser')}")
            
            # Create user object from payload
            user = self.create_jwt_user(payload)
            
            # Attach extra JWT data to request
            request.user_id = payload.get('sub')
            request.user_email = payload.get('email')
            request.user_role = payload.get('role')
            request.user_roles = payload.get('roles', [payload.get('role')])
            request.is_superuser = payload.get('is_superuser', False)
            request.is_staff = payload.get('is_staff', False)
            request.jti = payload.get('jti')
            request.session_id = payload.get('session_id')
            
            logger.info(f"Authentication successful for user {user.email} "
                       f"with role {user.role}")
            return (user, token)
            
        except pyjwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise AuthenticationFailed('Token expired')
        except pyjwt.DecodeError as e:
            logger.error(f"Token decode error: {e}")
            logger.error(f"Token that failed: '{token[:100]}...'")
            raise AuthenticationFailed('Invalid token format')
        except pyjwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise AuthenticationFailed('Invalid token')
        except AuthenticationFailed:
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}", exc_info=True)
            raise AuthenticationFailed('Authentication failed')
    
    def is_valid_jwt_format(self, token: str) -> bool:
        """
        Validate that token has the correct JWT format (3 parts separated by dots)
        """
        if not token or not isinstance(token, str):
            logger.error("Token is empty or not a string")
            return False
        
        # Clean the token - remove any quotes
        token = token.strip().strip('"\'')
        
        if len(token) < 10:
            logger.error(f"Token too short: {len(token)} chars")
            return False
        
        # JWT should have exactly 2 dots (3 parts)
        parts = token.split('.')
        if len(parts) != 3:
            logger.error(f"JWT has {len(parts)} parts, expected 3")
            return False
        
        # Each part should be non-empty
        for i, part in enumerate(parts):
            if not part:
                logger.error(f"JWT part {i} is empty")
                return False
            
            if ' ' in part:
                logger.error(f"JWT part {i} contains spaces")
                return False
        
        # Check for base64url characters
        base64url_pattern = r'^[A-Za-z0-9_-]+$'
        for i, part in enumerate(parts):
            if not re.match(base64url_pattern, part):
                logger.error(f"JWT part {i} contains invalid base64url characters")
                return False
        
        return True
    
    def extract_token(self, request):
        """
        Extract JWT token from request headers or cookies.
        
        FIXED: Better token extraction with validation
        """
        token = None
        
        # Try Authorization header first
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header:
            logger.debug(f"Raw Authorization header: '{auth_header[:100]}'")
            
            # Clean up the header
            auth_header = auth_header.strip()
            
            # Handle different formats
            if auth_header.lower().startswith('bearer '):
                # Extract token after "Bearer "
                token = auth_header[7:].strip()
            elif ' ' in auth_header:
                # Try to extract token from other formats
                parts = auth_header.split()
                if len(parts) >= 2:
                    # Take the last part if there are multiple parts
                    token = parts[-1].strip()
                else:
                    token = auth_header.strip()
            else:
                # No bearer prefix, might be just the token
                token = auth_header.strip()
            
            # Clean up the token
            if token:
                # Remove any quotes
                token = token.strip('"\'')
                
                # Remove any trailing spaces or newlines
                token = token.strip()
                
                # Log for debugging
                logger.debug(f"Extracted token from header (length: {len(token)})")
                
                # Validate it looks like a JWT
                if '.' not in token:
                    logger.warning("Extracted token doesn't contain dots, might not be a JWT")
                    token = None
        
        # If no token from header, try cookies
        if not token:
            # Try different cookie names
            cookie_names = ['access_token', 'token', 'jwt_token', 'auth_token']
            for cookie_name in cookie_names:
                if cookie_name in request.COOKIES:
                    token = request.COOKIES[cookie_name]
                    logger.debug(f"Found token in cookie '{cookie_name}' (length: {len(token)})")
                    break
        
        # Final cleanup
        if token:
            token = token.strip().strip('"\'').strip()
            
            # Basic validation
            if len(token) < 10:
                logger.error(f"Token too short after extraction: {len(token)} chars")
                return None
            
            # Check for common issues
            if '\n' in token or '\r' in token:
                logger.error("Token contains newline characters")
                token = token.replace('\n', '').replace('\r', '')
            
            if ' ' in token:
                logger.warning("Token contains spaces, removing them")
                # If it's a multi-part token with spaces, take the part that looks like a JWT
                parts = token.split()
                for part in parts:
                    if '.' in part and len(part) > 20:
                        token = part
                        break
        
        return token
    
    def create_jwt_user(self, payload: dict):
        """
        Create a Django-compatible user object from JWT payload.
        """
        
        class JWTUser:
            """
            Lightweight user class for JWT authentication.
            Compatible with Django and DRF's authentication system.
            """
            
            def __init__(self, payload):
                # Basic identity
                self.id = payload.get('sub')
                self.pk = payload.get('sub')
                self.username = payload.get('email', '')
                self.email = payload.get('email', '')
                
                # Role and permissions - CRITICAL FIX
                self.role = payload.get('role')
                if not self.role and 'roles' in payload:
                    self.role = payload['roles'][0] if payload['roles'] else 'member'
                
                self.roles = payload.get('roles', [self.role] if self.role else ['member'])
                
                # Get permission flags from payload
                self.is_superuser = payload.get('is_superuser', False)
                self.is_staff = payload.get('is_staff', False)
                
                # Override with role-based permissions if not explicitly set
                if not self.is_superuser and self.role in ['super_admin', 'admin']:
                    self.is_superuser = True
                if not self.is_staff and self.role in ['super_admin', 'admin', 'staff']:
                    self.is_staff = True
                
                # JWT-specific attributes
                self.jti = payload.get('jti')
                self.session_id = payload.get('session_id')
                
                # CRITICAL: These make DRF recognize the user as authenticated
                self.is_authenticated = True
                self.is_active = True
                self.is_anonymous = False
                
                self.backend = 'apps.core.jwt.authentication.JWTAuthentication'
                
                logger.debug(f"JWTUser created: {self.email}, "
                           f"role={self.role}, "
                           f"is_superuser={self.is_superuser}, "
                           f"is_staff={self.is_staff}")
            
            def _has_role(self, role_list):
                """Check if user has any of the specified roles"""
                return self.role in role_list if self.role else False
            
            def __str__(self):
                return f"JWTUser({self.email}, role={self.role})"
            
            def __repr__(self):
                return f"<JWTUser: {self.email} (id={self.id}, role={self.role})>"
            
            def get_username(self):
                return self.username
            
            # Permission methods
            def has_perm(self, perm, obj=None):
                # Super admin has all permissions
                if self.role == 'super_admin':
                    return True
                # Admin has most permissions except system-level
                if self.role == 'admin':
                    return not perm.startswith('system.')
                # Staff has limited permissions
                if self.role == 'staff':
                    return perm.startswith('user.view') or perm.startswith('content.')
                return False
            
            def has_perms(self, perm_list, obj=None):
                if self.role == 'super_admin':
                    return True
                # Check each permission based on role
                for perm in perm_list:
                    if not self.has_perm(perm, obj):
                        return False
                return True
            
            def has_module_perms(self, app_label):
                if self.role == 'super_admin':
                    return True
                if self.role == 'admin':
                    return app_label not in ['system', 'auth']
                if self.role == 'staff':
                    return app_label in ['content', 'user']
                return False
            
            def __eq__(self, other):
                if not isinstance(other, JWTUser):
                    return False
                return self.id == other.id
            
            def __hash__(self):
                return hash(self.id)
            
            def save(self, *args, **kwargs):
                raise NotImplementedError("JWT users cannot be saved to database")
            
            def delete(self, *args, **kwargs):
                raise NotImplementedError("JWT users cannot be deleted")
        
        return JWTUser(payload)
    
    def authenticate_header(self, request):
        """
        Return the WWW-Authenticate header value for 401 responses.
        """
        return f'{self.keyword} realm="api"'


class JWTAuthenticationOptional(JWTAuthentication):
    """
    Optional JWT authentication - doesn't fail if no token is provided.
    
    Useful for endpoints that work for both authenticated and anonymous users.
    """
    
    def authenticate(self, request):
        """
        Try to authenticate, but return None instead of failing.
        """
        try:
            return super().authenticate(request)
        except AuthenticationFailed as e:
            logger.debug(f"Optional JWT authentication failed: {e}, allowing anonymous access")
            return None