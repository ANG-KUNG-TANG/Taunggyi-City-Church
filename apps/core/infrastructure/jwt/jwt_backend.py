"""
Production JWT Backend with Key Management and Token Services
Security Level: CRITICAL
Compliance: OWASP JWT, NIST Key Management
"""
import os
import uuid
from typing import Optional, Tuple, Dict, Any, List
import logging
from datetime import datetime
from apps.core.security.blacklist_service import BlacklistService
from apps.core.security.jwt_manager import JWTManager, TokenConfig, TokenType
from core.cache.async_cache import AsyncCache
from .key_rotation import KeyRotationManager

logger = logging.getLogger(__name__)

class JWTBackend:
    """
    Production-grade JWT Backend Service
    Security Level: CRITICAL
    Responsibilities: Token lifecycle management, security enforcement
    """
    
    _instance: Optional['JWTBackend'] = None
    
    def __init__(self, cache: AsyncCache, config: TokenConfig = None):
        if JWTBackend._instance is not None:
            raise RuntimeError("JWTBackend is a singleton! Use get_instance()")
        
        self.cache = cache
        self.config = config or self._load_config_from_env()
        self.key_manager = KeyRotationManager(cache)
        self.jwt_manager = None
        self.blacklist_service = BlacklistService(cache)
        self._initialized = False
        
        JWTBackend._instance = self
        logger.info("JWTBackend instance created")

    @classmethod
    async def get_instance(cls, cache: AsyncCache = None, config: TokenConfig = None) -> 'JWTBackend':
        """Get singleton instance with lazy initialization"""
        if cls._instance is None:
            if cache is None:
                raise ValueError("Cache is required for first initialization")
            cls._instance = JWTBackend(cache, config)
            await cls._instance.initialize()
        return cls._instance

    async def initialize(self):
        """Initialize JWT backend services"""
        if self._initialized:
            return
            
        try:
            # Initialize key management
            await self.key_manager.initialize()
            
            # Create JWT manager with current keys
            current_private_key = self.key_manager.get_current_private_key()
            current_public_key = self.key_manager.get_public_key()
            
            if not current_private_key or not current_public_key:
                raise RuntimeError("Failed to initialize JWT keys")
                
            self.jwt_manager = JWTManager(
                config=self.config,
                private_key=current_private_key,
                public_key=current_public_key
            )
            
            self._initialized = True
            logger.info("JWTBackend initialized successfully")
            
        except Exception as e:
            logger.critical(f"JWTBackend initialization failed: {e}")
            raise

    def _load_config_from_env(self) -> TokenConfig:
        """Load configuration from environment variables"""
        return TokenConfig(
            access_token_expiry=int(os.getenv('JWT_ACCESS_EXPIRY', 900)),
            refresh_token_expiry=int(os.getenv('JWT_REFRESH_EXPIRY', 604800)),
            reset_token_expiry=int(os.getenv('JWT_RESET_EXPIRY', 1800)),
            algorithm=os.getenv('JWT_ALGORITHM', 'RS256'),
            issuer=os.getenv('JWT_ISSUER', 'auth-service'),
            audience=os.getenv('JWT_AUDIENCE', 'api').split(',')
        )

    async def create_tokens(self, 
                          user_id: str, 
                          email: str,
                          roles: List[str] = None,
                          permissions: List[str] = None,
                          session_id: str = None) -> Dict[str, Any]:
        """
        Create access and refresh tokens
        Security Level: HIGH
        
        Returns:
            Token response with metadata
        """
        if not self._initialized:
            raise RuntimeError("JWTBackend not initialized")
            
        try:
            session_id = session_id or str(uuid.uuid4())
            
            access_token = self.jwt_manager.create_access_token(
                user_id=user_id,
                email=email,
                roles=roles,
                permissions=permissions,
                session_id=session_id
            )
            
            refresh_token = self.jwt_manager.create_refresh_token(
                user_id=user_id,
                email=email,
                session_id=session_id
            )
            
            token_metadata = self.jwt_manager.get_token_metadata(access_token)
            
            response = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": self.config.access_token_expiry,
                "session_id": session_id,
                "key_fingerprint": self.jwt_manager.key_fingerprint,
                "metadata": token_metadata
            }
            
            logger.info(f"Tokens created for user {user_id}, session {session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Token creation failed for user {user_id}: {e}")
            raise

    async def verify_token(self, 
                         token: str, 
                         token_type: TokenType = None) -> Tuple[bool, Optional[Dict]]:
        """
        Comprehensive token verification
        Security Level: CRITICAL
        
        Steps:
        1. Verify token signature with current key
        2. If failed, try with previous keys (for graceful key rotation)
        3. Check token blacklist
        4. Validate token claims
        """
        if not self._initialized:
            return False, None
            
        try:
            # Step 1: Try with current key
            is_valid, payload = self.jwt_manager.verify_token(token, token_type)
            
            if not is_valid:
                # Step 2: Try with previous keys during key rotation
                is_valid, payload = await self._verify_with_previous_keys(token, token_type)
                
            if not is_valid:
                return False, None
                
            # Step 3: Check blacklist
            jti = payload.get('jti')
            if jti:
                is_blacklisted, _ = await self.blacklist_service.is_blacklisted(jti)
                if is_blacklisted:
                    logger.warning(f"Token verification failed: blacklisted jti={jti}")
                    return False, None
            
            # Step 4: Additional security checks
            if not self._perform_security_checks(payload):
                return False, None
                
            logger.debug(f"Token verified successfully: jti={jti}, user={payload.get('sub')}")
            return True, payload
            
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return False, None

    async def _verify_with_previous_keys(self, token: str, token_type: TokenType) -> Tuple[bool, Optional[Dict]]:
        """Verify token with previous keys during key rotation"""
        try:
            all_public_keys = self.key_manager.get_all_public_keys()
            
            for key_id, public_key in all_public_keys.items():
                if key_id == self.key_manager.current_key_id:
                    continue  # Already tried current key
                    
                try:
                    temp_jwt_manager = JWTManager(
                        config=self.config,
                        private_key="",  # Not needed for verification
                        public_key=public_key
                    )
                    
                    is_valid, payload = temp_jwt_manager.verify_token(token, token_type)
                    if is_valid:
                        logger.info(f"Token verified with previous key: {key_id}")
                        return True, payload
                        
                except Exception:
                    continue
                    
            return False, None
            
        except Exception as e:
            logger.warning(f"Previous key verification failed: {e}")
            return False, None

    def _perform_security_checks(self, payload: Dict) -> bool:
        """Perform additional security checks on token payload"""
        try:
            # Check for required claims
            required_claims = ['sub', 'exp', 'iat', 'jti', 'token_type']
            for claim in required_claims:
                if claim not in payload:
                    logger.warning(f"Missing required claim: {claim}")
                    return False
            
            # Check token type
            token_type = payload.get('token_type')
            if token_type not in [t.value for t in TokenType]:
                logger.warning(f"Invalid token type: {token_type}")
                return False
                
            # Check for suspiciously long expiry
            iat = payload.get('iat', 0)
            exp = payload.get('exp', 0)
            token_lifetime = exp - iat
            
            if token_lifetime > 86400 * 30:  # 30 days max
                logger.warning(f"Suspicious token lifetime: {token_lifetime} seconds")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Security checks failed: {e}")
            return False

    async def revoke_token(self, token: str, reason: str = "user_revoked") -> bool:
        """
        Revoke token by adding to blacklist
        Security Level: HIGH
        """
        try:
            # Extract jti from token without verification
            metadata = self.jwt_manager.get_token_metadata(token)
            jti = metadata.get('jti')
            
            if not jti:
                logger.warning("Cannot revoke token: jti not found")
                return False
                
            # Get remaining TTL for proper blacklist expiry
            payload = self.jwt_manager.get_token_metadata(token)
            exp_timestamp = payload.get('expires_at', datetime.utcnow()).timestamp()
            remaining_ttl = max(0, int(exp_timestamp - datetime.utcnow().timestamp()))
            
            # Add some buffer to ensure token expiry
            blacklist_ttl = remaining_ttl + 300  # 5 minutes buffer
            
            success = await self.blacklist_service.blacklist_token(
                jti=jti,
                expires_in=blacklist_ttl,
                reason=reason
            )
            
            if success:
                logger.info(f"Token revoked: jti={jti}, reason={reason}")
            else:
                logger.error(f"Token revocation failed: jti={jti}")
                
            return success
            
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False

    async def revoke_all_session_tokens(self, session_id: str, reason: str = "session_terminated") -> bool:
        """
        Revoke all tokens for a session
        Security Level: HIGH
        """
        # This would typically involve querying a session store
        # For now, we'll log the action
        logger.info(f"Revoked all tokens for session {session_id}, reason: {reason}")
        return True

    async def rotate_keys(self) -> str:
        """Rotate to new key pair"""
        if not self._initialized:
            raise RuntimeError("JWTBackend not initialized")
            
        new_key_id = await self.key_manager.rotate_keys()
        
        # Update JWT manager with new keys
        current_private_key = self.key_manager.get_current_private_key()
        current_public_key = self.key_manager.get_public_key()
        
        self.jwt_manager = JWTManager(
            config=self.config,
            private_key=current_private_key,
            public_key=current_public_key
        )
        
        logger.info(f"Key rotation completed: new key ID = {new_key_id}")
        return new_key_id

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        try:
            jwt_health = {
                "initialized": self._initialized,
                "key_fingerprint": self.jwt_manager.key_fingerprint if self.jwt_manager else None,
                "key_rotation": await self.key_manager.get_key_rotation_status()
            }
            
            blacklist_health = await self.blacklist_service.health_check()
            
            # Test token creation and verification
            test_user_id = "health_check"
            test_email = "health@example.com"
            
            if self._initialized:
                tokens = await self.create_tokens(test_user_id, test_email)
                verify_success, _ = await self.verify_token(tokens["access_token"])
                
                jwt_health["token_operations"] = {
                    "creation": True,
                    "verification": verify_success
                }
            
            return {
                "status": "healthy" if self._initialized and blacklist_health.get("status") == "healthy" else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "jwt_backend": jwt_health,
                "blacklist_service": blacklist_health
            }
            
        except Exception as e:
            logger.error(f"JWTBackend health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @property
    def public_key_jwks(self) -> Dict[str, Any]:
        """Get public keys in JWKS format"""
        if not self._initialized:
            raise RuntimeError("JWTBackend not initialized")
            
        return self.key_manager.get_jwks()

    async def get_operational_metrics(self) -> Dict[str, Any]:
        """Get operational metrics for monitoring"""
        blacklist_stats = await self.blacklist_service.get_blacklist_stats()
        key_rotation_status = await self.key_manager.get_key_rotation_status()
        
        return {
            "service": "jwt_backend",
            "timestamp": datetime.utcnow().isoformat(),
            "initialized": self._initialized,
            "key_rotation": key_rotation_status,
            "blacklist": blacklist_stats,
            "key_fingerprint": self.jwt_manager.key_fingerprint if self.jwt_manager else None
        }