# import jwt
# import secrets
# import hashlib
# from enum import Enum
# from dataclasses import dataclass
# from datetime import datetime, timedelta
# from typing import List, Optional, Dict, Any, Tuple
# from django.conf import settings
# from django.core.exceptions import ImproperlyConfigured
# import logging
# from cryptography.hazmat.primitives import serialization
# from cryptography.hazmat.primitives.asymmetric import rsa
# from cryptography.hazmat.backends import default_backend
# from cryptography.hazmat.primitives.asymmetric.types import PublicKeyTypes, PrivateKeyTypes


# logger = logging.getLogger(__name__)

# class TokenType(Enum):
#     ACCESS = 'access'
#     REFRESH = 'refresh'
#     RESET_PASSWORD = 'reset_password'
#     EMIL_VERIFICATION = 'email_verification'
    
# @dataclass(frozen=True)
# class TokenConfig:
#     access_token_exipry: int = 900
#     refresh_token_expirey: int = 604800
#     reset_token_expiry: int = 1800
#     algorithm: str = "RS256"
#     issue: str = "auth-service"
#     audience: List[str] = None
    
#     def __post_inti__(self):
#         if self.audience is None:
#             object.__setattr__(self, 'audience', ['api'])

# @dataclass(frozen=True)
# class TokenPayload:
#     user_id: str
    
# class JWTManager:
#     def __init__(self):
#         self.algorithm = getattr(settings, 'JWT_ALGORITHM', 'RS256')
#         self.access_token_lifetime = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', timedelta(minutes=15))
#         self.refresh_token_lifetime = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', timedelta(days=7))
#         self.leeway = getattr(settings, 'JWT_LEEWAY', timedelta(seconds=10))
        
#         # Load keys
#         self._load_keys()

#     def _load_keys(self):
#         """Load RSA keys for asymmetric encryption"""
#         try:
#             if self.algorithm.startswith('RS'):
#                 self.private_key = self._get_private_key()
#                 self.public_key = self._get_public_key()
#             else:
#                 self.secret_key = getattr(settings, 'JWT_SECRET_KEY')
#                 if not self.secret_key:
#                     raise ImproperlyConfigured("JWT_SECRET_KEY must be set for HS256 algorithm")
#         except Exception as e:
#             logger.error(f"Failed to load JWT keys: {e}")
#             raise

#     def _get_private_key(self) -> bytes:
#         """Get private key from environment or file"""
#         private_key_pem = getattr(settings, 'JWT_PRIVATE_KEY')
#         if not private_key_pem:
#             raise ImproperlyConfigured("JWT_PRIVATE_KEY must be set for RS256 algorithm")
#         return private_key_pem.encode('utf-8')

#     def _get_public_key(self) -> bytes:
#         """Get public key from environment or file"""
#         public_key_pem = getattr(settings, 'JWT_PUBLIC_KEY')
#         if not public_key_pem:
#             raise ImproperlyConfigured("JWT_PUBLIC_KEY must be set for RS256 algorithm")
#         return public_key_pem.encode('utf-8')

#     def create_access_token(self, payload: Dict[str, Any], jti: str = None) -> str:
#         """Create JWT access token with enhanced security"""
#         payload = payload.copy()
#         now = datetime.utcnow()
#         expire = now + self.access_token_lifetime
        
#         # Standard claims for security
#         standard_claims = {
#             'exp': expire,
#             'iat': now,
#             'nbf': now - self.leeway,  # Not before
#             'iss': getattr(settings, 'JWT_ISSUER', 'your-app'),
#             'aud': getattr(settings, 'JWT_AUDIENCE', 'your-app-users'),
#             'type': 'access',
#             'jti': jti or secrets.token_urlsafe(32),  # Unique token ID
#             'version': '1.0'
#         }
        
#         payload.update(standard_claims)
        
#         try:
#             if self.algorithm.startswith('RS'):
#                 token = jwt.encode(payload, self.private_key, algorithm=self.algorithm)
#             else:
#                 token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
#             logger.info(f"Access token created for user {payload.get('user_id')}, jti: {standard_claims['jti']}")
#             return token
#         except Exception as e:
#             logger.error(f"Failed to create access token: {e}")
#             raise

#     def create_refresh_token(self, payload: Dict[str, Any], family_id: str = None) -> Tuple[str, str]:
#         """Create refresh token with token family for rotation"""
#         payload = payload.copy()
#         now = datetime.utcnow()
#         expire = now + self.refresh_token_lifetime
#         jti = secrets.token_urlsafe(32)
#         family_id = family_id or secrets.token_urlsafe(16)

#         standard_claims = {
#             'exp': expire,
#             'iat': now,
#             'nbf': now - self.leeway,
#             'iss': getattr(settings, 'JWT_ISSUER', 'your-app'),
#             'aud': getattr(settings, 'JWT_AUDIENCE', 'your-app-users'),
#             'type': 'refresh',
#             'jti': jti,
#             'family': family_id,
#             'version': '1.0'
#         }

#         payload.update(standard_claims)

#         try:
#             if self.algorithm.startswith('RS'):
#                 token = jwt.encode(payload, self.private_key, algorithm=self.algorithm)
#             else:
#                 token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

#             logger.info(f"Refresh token created for user {payload.get('user_id')}, family: {family_id}")
#             return token, family_id
#         except Exception as e:
#             logger.error(f"Failed to create refresh token: {e}")
#             raise

#     def verify_token(self, token: str, token_type: str = None) -> Optional[Dict[str, Any]]:
#         """Verify JWT token with enhanced security checks"""
#         try:
#             if self.algorithm.startswith('RS'):
#                 payload = jwt.decode(
#                     token, 
#                     self.public_key, 
#                     algorithms=[self.algorithm],
#                     options={
#                         'verify_exp': True,
#                         'verify_iss': True,
#                         'verify_aud': True,
#                         'verify_signature': True
#                     },
#                     issuer=getattr(settings, 'JWT_ISSUER', 'your-app'),
#                     audience=getattr(settings, 'JWT_AUDIENCE', 'your-app-users'),
#                     leeway=self.leeway
#                 )
#             else:
#                 payload = jwt.decode(
#                     token,
#                     self.secret_key,
#                     algorithms=[self.algorithm],
#                     options={
#                         'verify_exp': True,
#                         'verify_iss': True,
#                         'verify_aud': True,
#                         'verify_signature': True
#                     },
#                     issuer=getattr(settings, 'JWT_ISSUER', 'your-app'),
#                     audience=getattr(settings, 'JWT_AUDIENCE', 'your-app-users'),
#                     leeway=self.leeway
#                 )

#             # Additional type validation
#             if token_type and payload.get('type') != token_type:
#                 logger.warning(f"Token type mismatch. Expected: {token_type}, Got: {payload.get('type')}")
#                 return None

#             # Validate token version
#             if payload.get('version') != '1.0':
#                 logger.warning(f"Invalid token version: {payload.get('version')}")
#                 return None

#             return payload

#         except jwt.ExpiredSignatureError:
#             logger.warning("Token has expired")
#             return None
#         except jwt.InvalidTokenError as e:
#             logger.warning(f"Invalid token: {e}")
#             return None
#         except Exception as e:
#             logger.error(f"Token verification error: {e}")
#             return None

#     def get_token_fingerprint(self, token: str) -> str:
#         """Create fingerprint for token tracking"""
#         return hashlib.sha256(token.encode('utf-8')).hexdigest()

#     def extract_jti(self, token: str) -> Optional[str]:
#         """Extract JTI from token without verification (for blacklisting)"""
#         try:
#             payload = jwt.decode(token, options={"verify_signature": False})
#             return payload.get('jti')
#         except jwt.DecodeError:
#             return None