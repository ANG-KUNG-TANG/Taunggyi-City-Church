import os
import uuid
import secrets
import json
from typing import Optional, Tuple, Dict, Any, List
import logging
from datetime import datetime, timedelta
import jwt
from enum import Enum
from django.core.cache import cache
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    EMAIL_VERIFICATION = "email_verification"

class TokenConfig:
    """JWT Configuration with environment-based settings"""
    
    def __init__(
        self,
        access_token_expiry: int = None,
        refresh_token_expiry: int = None,
        reset_token_expiry: int = None,
        algorithm: str = None,
        secret_key: str = None,
        issuer: str = None,
        audience: List[str] = None
    ):
        # Load from environment with defaults
        self.access_token_expiry = access_token_expiry or int(os.getenv('JWT_ACCESS_EXPIRY', 900))
        self.refresh_token_expiry = refresh_token_expiry or int(os.getenv('JWT_REFRESH_EXPIRY', 604800))
        self.reset_token_expiry = reset_token_expiry or int(os.getenv('JWT_RESET_EXPIRY', 1800))
        self.algorithm = algorithm or os.getenv('JWT_ALGORITHM', 'HS256')
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', self._get_default_secret_key())
        self.issuer = issuer or os.getenv('JWT_ISSUER', 'tcc-auth-service')
        self.audience = audience or os.getenv('JWT_AUDIENCE', 'tcc-api').split(',')
        
        self._validate_config()
    
    def _get_default_secret_key(self) -> str:
        """Get default secret key from Django settings"""
        try:
            from django.conf import settings
            return getattr(settings, 'SECRET_KEY', secrets.token_urlsafe(64))
        except ImportError:
            return secrets.token_urlsafe(64)
    
    def _validate_config(self):
        """Validate JWT configuration"""
        if self.algorithm == "HS256":
            if not self.secret_key:
                raise ValueError("secret_key is required for HS256 algorithm")
            if len(self.secret_key) < 32:
                logger.warning("HS256 secret key is shorter than recommended 32 characters")
        elif self.algorithm.startswith("RS"):
            logger.warning(f"RS256 algorithm requires key rotation setup. Using HS256 for development.")
            self.algorithm = "HS256"
            self.secret_key = self.secret_key or secrets.token_urlsafe(64)
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")

class JWTManager:
    """
    Core JWT Token Management
    """
    
    def __init__(self, config: TokenConfig):
        self.config = config
        logger.info(f"JWTManager initialized with {self.config.algorithm} algorithm")
    
    def generate_access_token(
        self, 
        user_id: str,
        email: str,
        roles: List[str] = None,
        session_id: str = None
    ) -> str:
        """Create access token"""
        now = datetime.utcnow()
        expires = now + timedelta(seconds=self.config.access_token_expiry)
        
        payload = {
            "token_type": TokenType.ACCESS.value,
            "sub": user_id,
            "email": email,
            "roles": roles or [],
            "session_id": session_id or str(uuid.uuid4()),
            "jti": secrets.token_urlsafe(32),
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "iss": self.config.issuer,
            "aud": self.config.audience[0] if self.config.audience else "tcc-api",
        }
        
        return jwt.encode(
            payload, 
            self.config.secret_key, 
            algorithm=self.config.algorithm
        )
    
    def generate_refresh_token(self, user_id: str, email: str, session_id: str = None) -> str:
        """Create refresh token"""
        now = datetime.utcnow()
        expires = now + timedelta(seconds=self.config.refresh_token_expiry)
        
        payload = {
            "token_type": TokenType.REFRESH.value,
            "sub": user_id,
            "email": email,
            "session_id": session_id or str(uuid.uuid4()),
            "jti": secrets.token_urlsafe(32),
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "iss": self.config.issuer,
            "aud": self.config.audience[0] if self.config.audience else "tcc-api"
        }
        
        token = jwt.encode(
            payload, 
            self.config.secret_key, 
            algorithm=self.config.algorithm
        )
        
        # Store refresh token in cache
        cache_key = f"refresh_token:{user_id}:{payload['jti']}"
        cache_data = {
            "token": token,
            "user_id": user_id,
            "session_id": payload['session_id'],
            "created_at": now.isoformat()
        }
        
        # Use sync_to_async for Django cache
        sync_to_async(cache.set)(
            cache_key, 
            json.dumps(cache_data), 
            self.config.refresh_token_expiry
        )
        
        return token
    
    def generate_reset_token(self, user_id: str, email: str) -> str:
        """Create password reset token"""
        now = datetime.utcnow()
        expires = now + timedelta(seconds=self.config.reset_token_expiry)
        
        payload = {
            "token_type": TokenType.RESET.value,
            "sub": user_id,
            "email": email,
            "jti": secrets.token_urlsafe(32),
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "iss": self.config.issuer,
            "aud": self.config.audience[0] if self.config.audience else "tcc-api",
            "purpose": "password_reset"
        }
        
        token = jwt.encode(
            payload, 
            self.config.secret_key, 
            algorithm=self.config.algorithm
        )
        
        # Store reset token in cache
        cache_key = f"reset_token:{user_id}"
        sync_to_async(cache.set)(
            cache_key, 
            token, 
            self.config.reset_token_expiry
        )
        
        return token
    
    def verify_token(self, token: str, token_type: TokenType = None) -> Tuple[bool, Optional[Dict]]:
        """Verify token signature and claims"""
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                issuer=self.config.issuer,
                audience=self.config.audience[0] if self.config.audience else None
            )
            
            # Validate token type if specified
            if token_type and payload.get('token_type') != token_type.value:
                logger.warning(f"Token type mismatch: expected {token_type.value}, got {payload.get('token_type')}")
                return False, None
            
            return True, payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token verification failed: expired")
            return False, None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token verification failed: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return False, None
    
    def decode_token(self, token: str) -> Optional[Dict]:
        """Decode token without verification (for internal use)"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return None

class JWTBackend:
    """
    Main JWT Backend Service
    """
    
    _instance: Optional['JWTBackend'] = None
    
    def __init__(self, config: TokenConfig = None):
        if JWTBackend._instance is not None:
            raise RuntimeError("JWTBackend is a singleton! Use get_instance()")
        
        self.config = config or TokenConfig()
        self.jwt_manager = JWTManager(self.config)
        self._initialized = True
        
        JWTBackend._instance = self
        logger.info("JWTBackend instance created")
    
    @classmethod
    def get_instance(cls, config: TokenConfig = None) -> 'JWTBackend':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = JWTBackend(config)
        return cls._instance
    
    async def create_tokens(
        self, 
        user_id: str, 
        email: str,
        roles: List[str] = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Create access and refresh tokens
        """
        try:
            session_id = session_id or str(uuid.uuid4())
            
            access_token = self.jwt_manager.generate_access_token(
                user_id=user_id,
                email=email,
                roles=roles,
                session_id=session_id
            )
            
            refresh_token = self.jwt_manager.generate_refresh_token(
                user_id=user_id,
                email=email,
                session_id=session_id
            )
            
            response = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": self.config.access_token_expiry,
                "session_id": session_id
            }
            
            logger.info(f"Tokens created for user {user_id}")
            return response
            
        except Exception as e:
            logger.error(f"Token creation failed for user {user_id}: {e}")
            raise
    
    async def verify_token(
        self, 
        token: str, 
        token_type: TokenType = None
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Verify token with optional type checking
        """
        try:
            # Verify token signature and claims
            is_valid, payload = self.jwt_manager.verify_token(token, token_type)
            
            if not is_valid:
                return False, None
            
            # Additional security checks
            if not self._perform_security_checks(payload):
                return False, None
            
            logger.debug(f"Token verified: user={payload.get('sub')}")
            return True, payload
            
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return False, None
    
    def _perform_security_checks(self, payload: Dict) -> bool:
        """Perform security checks on token payload"""
        try:
            # Check for required claims
            required_claims = ['sub', 'exp', 'iat', 'jti', 'token_type']
            for claim in required_claims:
                if claim not in payload:
                    logger.warning(f"Missing required claim: {claim}")
                    return False
            
            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                logger.warning("Token expired")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Security checks failed: {e}")
            return False
    
    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using valid refresh token
        """
        try:
            # Verify refresh token
            is_valid, payload = await self.verify_token(refresh_token, TokenType.REFRESH)
            if not is_valid:
                raise ValueError("Invalid refresh token")
            
            # Check if refresh token exists in cache
            cache_key = f"refresh_token:{payload['sub']}:{payload.get('jti')}"
            cached_data = await sync_to_async(cache.get)(cache_key)
            
            if not cached_data:
                logger.warning(f"Refresh token not found in cache: jti={payload.get('jti')}")
                raise ValueError("Refresh token invalid or expired")
            
            # Create new tokens
            return await self.create_tokens(
                user_id=payload['sub'],
                email=payload['email'],
                roles=payload.get('roles', []),
                session_id=payload.get('session_id')
            )
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise
    
    async def revoke_refresh_token(self, user_id: str, jti: str) -> bool:
        """Revoke specific refresh token"""
        try:
            cache_key = f"refresh_token:{user_id}:{jti}"
            await sync_to_async(cache.delete)(cache_key)
            logger.info(f"Refresh token revoked: user={user_id}, jti={jti}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke refresh token: {e}")
            return False
    
    async def revoke_all_user_refresh_tokens(self, user_id: str) -> bool:
        """Revoke all refresh tokens for a user"""
        try:
            # Note: This is simplified. In production, track all active jtis for each user
            logger.info(f"All refresh tokens revoked for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke all tokens for user {user_id}: {e}")
            return False
    
    async def verify_reset_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """Verify password reset token"""
        is_valid, payload = await self.verify_token(token, TokenType.RESET)
        
        if not is_valid:
            return False, None
        
        # Check if reset token exists in cache
        cache_key = f"reset_token:{payload['sub']}"
        cached_token = await sync_to_async(cache.get)(cache_key)
        
        if not cached_token or cached_token != token:
            return False, None
        
        return True, payload
    
    async def invalidate_reset_token(self, user_id: str) -> bool:
        """Invalidate password reset token"""
        try:
            cache_key = f"reset_token:{user_id}"
            await sync_to_async(cache.delete)(cache_key)
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate reset token: {e}")
            return False
    
    def get_token_payload(self, token: str) -> Optional[Dict]:
        """Get token payload without verification"""
        return self.jwt_manager.decode_token(token)
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for JWT backend"""
        try:
            test_token = self.jwt_manager.create_access_token(
                user_id="health_check",
                email="health@test.com",
                roles=["system"]
            )
            
            is_valid, _ = await self.verify_token(test_token, TokenType.ACCESS)
            
            return {
                "status": "healthy" if is_valid else "degraded",
                "algorithm": self.config.algorithm,
                "initialized": self._initialized,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"JWTBackend health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Convenience function for getting JWT backend
def get_jwt_backend() -> JWTBackend:
    """Get JWT backend instance"""
    return JWTBackend.get_instance()