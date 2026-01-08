import os
import uuid
import secrets
import json
from typing import Optional, Tuple, Dict, Any, List
import logging
from datetime import datetime, timedelta
import jwt as pyjwt
from enum import Enum
from django.core.cache import cache
from asgiref.sync import sync_to_async
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from django.conf import settings

logger = logging.getLogger(__name__)

class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    EMAIL_VERIFICATION = "email_verification"

class TokenConfig:
    """JWT Configuration with proper key handling"""
    
    def __init__(
        self,
        access_token_expiry: int = None,
        refresh_token_expiry: int = None,
        reset_token_expiry: int = None,
        algorithm: str = None,
        secret_key: str = None,
        private_key: str = None,
        public_key: str = None,
        issuer: str = None,
        audience: List[str] = None
    ):
        # FIXED: Get secret key with proper priority
        # Priority: parameter > environment > Django JWT_CONFIG > Django SECRET_KEY
        jwt_config = getattr(settings, 'JWT_CONFIG', {})
        
        env_secret_key = os.getenv('JWT_SECRET_KEY')
        settings_jwt_secret = jwt_config.get('SECRET_KEY')
        settings_secret_key = getattr(settings, 'SECRET_KEY', None)
        
        self.secret_key = (
            secret_key or 
            env_secret_key or
            settings_jwt_secret or
            settings_secret_key
        )
        
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be configured!")
        
        # Log which key source is being used (first 10 chars for security)
        logger.info(f"JWT Secret Key loaded (first 10 chars): {self.secret_key[:10]}...")
        
        # Issuer and Audience configuration
        self.issuer = (
            issuer or 
            jwt_config.get('ISSUER') or 
            os.getenv('JWT_ISSUER', 'auth-service')
        )
        
        audience_str = (
            audience or 
            jwt_config.get('AUDIENCE') or 
            os.getenv('JWT_AUDIENCE', 'api')
        )
        
        if isinstance(audience_str, str):
            self.audience = [audience_str] if audience_str else ['api']
        else:
            self.audience = audience_str or ['api']
        
        # Token expiry times
        self.access_token_expiry = (
            access_token_expiry or 
            jwt_config.get('ACCESS_TOKEN_EXPIRY') or 
            int(os.getenv('JWT_ACCESS_EXPIRY', 900))  # 15 minutes default
        )
        
        self.refresh_token_expiry = (
            refresh_token_expiry or 
            jwt_config.get('REFRESH_TOKEN_EXPIRY') or 
            int(os.getenv('JWT_REFRESH_EXPIRY', 604800))  # 7 days default
        )
        
        self.reset_token_expiry = (
            reset_token_expiry or 
            jwt_config.get('RESET_TOKEN_EXPIRY') or 
            int(os.getenv('JWT_RESET_EXPIRY', 1800))
        )
        
        self.algorithm = (
            algorithm or 
            jwt_config.get('ALGORITHM') or 
            os.getenv('JWT_ALGORITHM', 'HS256')
        ).upper()
        
        self.private_key = (
            private_key or 
            jwt_config.get('PRIVATE_KEY') or 
            os.getenv('JWT_PRIVATE_KEY')
        )
        
        self.public_key = (
            public_key or 
            jwt_config.get('PUBLIC_KEY') or 
            os.getenv('JWT_PUBLIC_KEY')
        )
        
        self._validate_config()
        
        logger.info(f"TokenConfig initialized - Issuer: {self.issuer}, Audience: {self.audience}")
        logger.info(f"Algorithm: {self.algorithm}, Access expiry: {self.access_token_expiry}s")
    
    def _validate_config(self):
        """Validate JWT configuration"""
        if self.algorithm.startswith('HS'):
            if not self.secret_key:
                raise ValueError("JWT_SECRET_KEY is required for HS256 algorithm")
        elif self.algorithm.startswith('RS'):
            if not self.private_key or not self.public_key:
                raise ValueError("Private and public keys are required for RS256 algorithm")
        
        logger.info(f"JWT configuration validated for {self.algorithm}")

class JWTManager:
    """Core JWT Token Management with async support"""
    
    def __init__(self, config: TokenConfig):
        self.config = config
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        logger.info(f"JWTManager initialized with {self.config.algorithm} algorithm")
    
    def _get_signing_key(self):
        """Get the appropriate signing key based on algorithm"""
        if self.config.algorithm.startswith('RS') and self.config.private_key:
            return self.config.private_key
        return self.config.secret_key
    
    def _get_verification_key(self):
        """Get the appropriate verification key based on algorithm"""
        if self.config.algorithm.startswith('RS') and self.config.public_key:
            return self.config.public_key
        return self.config.secret_key
    
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
        
        # Ensure user_id is string
        user_id_str = str(user_id)
        
        payload = {
            "token_type": TokenType.ACCESS.value,
            "sub": user_id_str,
            "email": email,
            "roles": roles or [],
            "session_id": session_id or str(uuid.uuid4()),
            "jti": secrets.token_urlsafe(32),
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "iss": self.config.issuer,
            "aud": self.config.audience[0] if self.config.audience else "api",
        }
        
        try:
            signing_key = self._get_signing_key()
            logger.debug(f"Signing token with key (first 10 chars): {signing_key[:10]}...")
            logger.debug(f"Token payload: sub={user_id_str}, email={email}, exp={expires}")
            
            token = pyjwt.encode(
                payload, 
                signing_key, 
                algorithm=self.config.algorithm
            )
            
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            
            logger.info(f"Access token created for user {email}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to create access token: {e}", exc_info=True)
            raise
    
    def generate_refresh_token(self, user_id: str, email: str, session_id: str = None) -> str:
        """Create refresh token"""
        now = datetime.utcnow()
        expires = now + timedelta(seconds=self.config.refresh_token_expiry)
        
        user_id_str = str(user_id)
        
        payload = {
            "token_type": TokenType.REFRESH.value,
            "sub": user_id_str,
            "email": email,
            "session_id": session_id or str(uuid.uuid4()),
            "jti": secrets.token_urlsafe(32),
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "iss": self.config.issuer,
            "aud": self.config.audience[0] if self.config.audience else "api"
        }
        
        try:
            token = pyjwt.encode(
                payload, 
                self._get_signing_key(), 
                algorithm=self.config.algorithm
            )
            
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            
            # Store refresh token in cache
            self._store_refresh_token(user_id_str, payload['jti'], token, session_id)
            
            logger.info(f"Refresh token created for user {email}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}", exc_info=True)
            raise
    
    def _store_refresh_token(self, user_id: str, jti: str, token: str, session_id: str):
        """Store refresh token in cache"""
        try:
            cache_data = {
                "token": token,
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            cache_key = f"refresh_token:{user_id}:{jti}"
            cache.set(
                cache_key, 
                json.dumps(cache_data), 
                self.config.refresh_token_expiry
            )
            logger.debug(f"Refresh token stored in cache with key: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to store refresh token in cache: {e}")
    
    def verify_token_sync(self, token: str, token_type: TokenType = None) -> Tuple[bool, Optional[Dict]]:
        """Verify token signature and claims (synchronous)"""
        try:
            verification_key = self._get_verification_key()
            logger.debug(f"Verifying token with algorithm: {self.config.algorithm}")
            logger.debug(f"Verification key type: {type(verification_key)}")
            logger.debug(f"Verification key (first 20 chars): {str(verification_key)[:20] if verification_key else 'None'}")
            
            # Log token info (first and last 10 chars)
            token_str = token if isinstance(token, str) else str(token)
            logger.debug(f"Token to verify (first/last 10 chars): {token_str[:10]}...{token_str[-10:]}")
            
            # Decode with verification
            options = {
                'verify_exp': True,
                'verify_iss': True,
                'verify_aud': True,
                'verify_signature': True,
                'require': ['exp', 'iat', 'sub']
            }
            
            logger.debug(f"Issuer config: {self.config.issuer}")
            logger.debug(f"Audience config: {self.config.audience}")
            
            decoded = pyjwt.decode(
                token,
                verification_key,
                algorithms=[self.config.algorithm],
                issuer=self.config.issuer,
                audience=self.config.audience,
                options=options,
                leeway=10  # 10 seconds leeway for clock skew
            )
            
            # Ensure 'sub' is string
            if 'sub' in decoded and not isinstance(decoded['sub'], str):
                decoded['sub'] = str(decoded['sub'])
            
            # Validate token type if specified
            if token_type and decoded.get('token_type') != token_type.value:
                logger.warning(f"Token type mismatch: expected {token_type.value}, got {decoded.get('token_type')}")
                return False, None
            
            logger.debug(f"Token verified successfully for user {decoded.get('email')}")
            return True, decoded
            
        except pyjwt.ExpiredSignatureError:
            logger.warning("Token verification failed: expired")
            return False, None
        except pyjwt.InvalidIssuerError as e:
            logger.warning(f"Token verification failed: invalid issuer. Expected '{self.config.issuer}', error: {e}")
            return False, None
        except pyjwt.InvalidAudienceError as e:
            logger.warning(f"Token verification failed: invalid audience. Expected '{self.config.audience}', error: {e}")
            return False, None
        except pyjwt.InvalidSignatureError as e:
            logger.error(f"Token verification failed: INVALID SIGNATURE - {e}")
            logger.error(f"Verification key (first 20 chars): {str(verification_key)[:20] if verification_key else 'None'}")
            logger.error(f"Algorithm: {self.config.algorithm}")
            return False, None
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}", exc_info=True)
            return False, None
    
    async def verify_refresh_token(self, token: str) -> Optional[Dict]:
        """Verify refresh token asynchronously and return payload if valid"""
        try:
            logger.debug(f"Starting verification of refresh token ending in: ...{token[-10:] if len(token) > 10 else token}")
            
            loop = asyncio.get_event_loop()
            
            verify_sync = partial(
                self.verify_token_sync,
                token=token,
                token_type=TokenType.REFRESH
            )
            
            # Run verification in thread pool
            is_valid, payload = await loop.run_in_executor(
                self.thread_pool,
                verify_sync
            )
            
            if not is_valid:
                logger.warning(f"Refresh token verification failed for token ending in: ...{token[-10:] if len(token) > 10 else token}")
                # Log why it failed by checking the token manually
                try:
                    # Try to decode without verification to see what's in it
                    decoded_without_verify = pyjwt.decode(token, options={"verify_signature": False})
                    logger.warning(f"Token content (without verification): {decoded_without_verify}")
                    
                    # Check if expired
                    exp = decoded_without_verify.get('exp')
                    if exp:
                        exp_time = datetime.fromtimestamp(exp)
                        now = datetime.now()
                        if exp_time < now:
                            logger.warning(f"Token expired at {exp_time}, current time is {now}")
                except Exception as decode_error:
                    logger.warning(f"Could not decode token even without verification: {decode_error}")
                
                return None
            
            logger.debug(f"Refresh token verified for user {payload.get('email', 'unknown')}")
            return payload
        
        except Exception as e:
            logger.error(f"Error verifying refresh token: {e}", exc_info=True)
            return None
    
    async def is_token_blacklisted(self, user_id: str, token_id: str) -> bool:
        """Check if token is blacklisted in cache"""
        try:
            cache_key = f"refresh_token:{user_id}:{token_id}"
            
            def check_cache():
                cached = cache.get(cache_key)
                logger.debug(f"Cache check for {cache_key}: {'found' if cached else 'not found'}")
                return cached is None  # If not in cache, it's blacklisted/revoked
            
            loop = asyncio.get_event_loop()
            is_blacklisted = await loop.run_in_executor(
                self.thread_pool,
                check_cache
            )
            
            if is_blacklisted:
                logger.warning(f"Token blacklisted: user_id={user_id}, token_id={token_id}")
            
            return is_blacklisted
            
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            return False  # Assume not blacklisted if error
    
    async def generate_access_token_async(
        self, 
        user_id: str,
        email: str,
        roles: List[str] = None,
        session_id: str = None
    ) -> str:
        """Generate access token asynchronously"""
        loop = asyncio.get_event_loop()
        
        generate_sync = partial(
            self.generate_access_token,
            user_id=user_id,
            email=email,
            roles=roles,
            session_id=session_id
        )
        
        return await loop.run_in_executor(
            self.thread_pool,
            generate_sync
        )

class JWTBackend:
    """Main JWT Backend Service with async support"""
    
    _instance: Optional['JWTBackend'] = None
    _lock = asyncio.Lock()
    
    def __init__(self, config: TokenConfig = None, cache=None):
        if JWTBackend._instance is not None:
            raise RuntimeError("JWTBackend is a singleton! Use get_instance()")
        
        self.config = config or TokenConfig()
        self.jwt_manager = JWTManager(self.config)
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.cache = cache
        
        JWTBackend._instance = self
        logger.info("JWTBackend instance created")
    
    @classmethod
    def get_instance(cls, config: TokenConfig = None, cache=None) -> 'JWTBackend':
        """Get singleton instance (thread-safe)"""
        if cls._instance is None:
            cls._instance = JWTBackend(config, cache)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)"""
        cls._instance = None
    
    def _get_verification_key(self):
        """Get verification key from jwt_manager"""
        return self.jwt_manager._get_verification_key()
    
    def verify_token_sync(self, token: str, token_type: TokenType = None) -> Tuple[bool, Optional[Dict]]:
        """Verify token synchronously (for DRF compatibility)"""
        return self.jwt_manager.verify_token_sync(token, token_type)
    
    async def create_tokens(
        self, 
        user_id: str, 
        email: str,
        roles: List[str] = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Create access and refresh tokens asynchronously"""
        loop = asyncio.get_event_loop()
        
        create_tokens_sync = partial(
            self._create_tokens_sync,
            user_id=str(user_id),  # Ensure string
            email=email,
            roles=roles,
            session_id=session_id
        )
        
        return await loop.run_in_executor(
            self.thread_pool,
            create_tokens_sync
        )
    
    def _create_tokens_sync(
        self,
        user_id: str,
        email: str,
        roles: List[str] = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Synchronous token creation"""
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
            "token_type": "bearer",
            "expires_in": self.config.access_token_expiry,
            "expires_at": (datetime.utcnow() + timedelta(seconds=self.config.access_token_expiry)).isoformat(),
            "session_id": session_id
        }
        
        logger.info(f"Tokens created for user {email}")
        return response
    
    async def verify_token(
        self, 
        token: str, 
        token_type: TokenType = None
    ) -> Tuple[bool, Optional[Dict]]:
        """Verify token asynchronously"""
        loop = asyncio.get_event_loop()
        
        verify_sync = partial(
            self.jwt_manager.verify_token_sync,
            token=token,
            token_type=token_type
        )
        
        return await loop.run_in_executor(
            self.thread_pool,
            verify_sync
        )
    
    async def verify_refresh_token(self, token: str) -> Optional[Dict]:
        """Verify refresh token asynchronously - returns payload or None"""
        return await self.jwt_manager.verify_refresh_token(token)
    
    async def is_token_blacklisted(self, user_id: str, token_id: str) -> bool:
        """Check if token is blacklisted in cache"""
        return await self.jwt_manager.is_token_blacklisted(user_id, token_id)
    
    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using valid refresh token"""
        is_valid, payload = await self.verify_token(refresh_token, TokenType.REFRESH)
        if not is_valid:
            raise ValueError("Invalid refresh token")
        
        @sync_to_async
        def check_cache():
            cache_key = f"refresh_token:{payload['sub']}:{payload.get('jti')}"
            return cache.get(cache_key)
        
        cached_data = await check_cache()
        
        if not cached_data:
            logger.warning(f"Refresh token not found in cache: jti={payload.get('jti')}")
            raise ValueError("Refresh token invalid or expired")
        
        return await self.create_tokens(
            user_id=payload['sub'],
            email=payload['email'],
            roles=payload.get('roles', []),
            session_id=payload.get('session_id')
        )
    
    async def revoke_refresh_token(self, user_id: str, jti: str) -> bool:
        """Revoke specific refresh token"""
        @sync_to_async
        def delete_from_cache():
            cache_key = f"refresh_token:{user_id}:{jti}"
            return cache.delete(cache_key)
        
        try:
            success = await delete_from_cache()
            if success:
                logger.info(f"Refresh token revoked: user={user_id}, jti={jti}")
            return success
        except Exception as e:
            logger.error(f"Failed to revoke refresh token: {e}")
            return False
    
    def get_token_payload(self, token: str) -> Optional[Dict]:
        """Get token payload without verification"""
        try:
            return pyjwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return None
    
    async def generate_access_token_async(
        self, 
        user_id: str,
        email: str,
        roles: List[str] = None,
        session_id: str = None
    ) -> str:
        """Generate access token asynchronously"""
        return await self.jwt_manager.generate_access_token_async(
            user_id=user_id,
            email=email,
            roles=roles,
            session_id=session_id
        )

def get_jwt_backend() -> JWTBackend:
    """Get JWT backend instance"""
    return JWTBackend.get_instance()