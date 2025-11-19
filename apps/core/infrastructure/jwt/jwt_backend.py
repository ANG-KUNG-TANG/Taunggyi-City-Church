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
from apps.core.infrastructure.jwt.key_rotation import KeyRotationManager
from apps.core.security.blacklist_service import BlacklistService
from apps.core.security.jwt_manager import JWTManager, TokenConfig, TokenType

logger = logging.getLogger(__name__)

class JWTBackend:
    """
    Production-grade JWT Backend Service
    Security Level: CRITICAL
    Responsibilities: Token lifecycle management, security enforcement
    """
    
    _instance: Optional['JWTBackend'] = None
    
    def __init__(self, cache=None, config: TokenConfig = None):
        if JWTBackend._instance is not None:
            raise RuntimeError("JWTBackend is a singleton! Use get_instance()")
        
        self.cache = cache
        self.config = config or self._load_config_from_env()
        self.key_manager = KeyRotationManager(cache) if cache else None
        self.jwt_manager = None
        self.blacklist_service = BlacklistService(cache) if cache else None
        self._initialized = False
        
        JWTBackend._instance = self
        logger.info("JWTBackend instance created")

    @classmethod
    def get_instance(cls, cache=None, config: TokenConfig = None) -> 'JWTBackend':
        """Get singleton instance with lazy initialization"""
        if cls._instance is None:
            cls._instance = JWTBackend(cache, config)
        return cls._instance

    async def initialize(self):
        """Initialize JWT backend services"""
        if self._initialized:
            return
            
        try:
            if self.key_manager:
                await self.key_manager.initialize()
                
                # Create JWT manager with current keys
                current_private_key = self.key_manager.get_current_private_key()
                current_public_key = self.key_manager.get_public_key()
                
                if current_private_key and current_public_key:
                    self.jwt_manager = JWTManager(
                        config=self.config,
                        private_key=current_private_key,
                        public_key=current_public_key
                    )
                else:
                    # Fallback to HS256 if RSA keys not available
                    logger.warning("RSA keys not available, using HS256 fallback")
                    self.jwt_manager = self._create_hs256_manager()
            else:
                # No cache, use HS256
                self.jwt_manager = self._create_hs256_manager()
            
            self._initialized = True
            logger.info("JWTBackend initialized successfully")
            
        except Exception as e:
            logger.critical(f"JWTBackend initialization failed: {e}")
            # Fallback to HS256
            self.jwt_manager = self._create_hs256_manager()
            self._initialized = True

    def _create_hs256_manager(self) -> JWTManager:
        """Create HS256 JWT manager as fallback"""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        
        # Generate temporary RSA keys for HS256 fallback
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        # Use HS256 algorithm
        hs256_config = TokenConfig(
            access_token_expiry=self.config.access_token_expiry,
            refresh_token_expiry=self.config.refresh_token_expiry,
            reset_token_expiry=self.config.reset_token_expiry,
            algorithm="HS256",  # Use HS256 instead of RS256
            issuer=self.config.issuer,
            audience=self.config.audience
        )
        
        return JWTManager(
            config=hs256_config,
            private_key=private_pem,
            public_key=public_pem
        )

    def _load_config_from_env(self) -> TokenConfig:
        """Load configuration from environment variables"""
        return TokenConfig(
            access_token_expiry=int(os.getenv('JWT_ACCESS_EXPIRY', 900)),
            refresh_token_expiry=int(os.getenv('JWT_REFRESH_EXPIRY', 604800)),
            reset_token_expiry=int(os.getenv('JWT_RESET_EXPIRY', 1800)),
            algorithm=os.getenv('JWT_ALGORITHM', 'HS256'),  # Default to HS256
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
        """
        if not self._initialized:
            await self.initialize()
            
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
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Verify token signature
            is_valid, payload = self.jwt_manager.verify_token(token, token_type)
            
            if not is_valid:
                return False, None
                
            # Check blacklist if available
            if self.blacklist_service:
                jti = payload.get('jti')
                if jti:
                    is_blacklisted, _ = await self.blacklist_service.is_blacklisted(jti)
                    if is_blacklisted:
                        logger.warning(f"Token verification failed: blacklisted jti={jti}")
                        return False, None
            
            # Additional security checks
            if not self._perform_security_checks(payload):
                return False, None
                
            logger.debug(f"Token verified successfully: jti={payload.get('jti')}, user={payload.get('sub')}")
            return True, payload
            
        except Exception as e:
            logger.error(f"Token verification error: {e}")
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
            valid_types = [t.value for t in TokenType]
            if token_type not in valid_types:
                logger.warning(f"Invalid token type: {token_type}")
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
        if not self.blacklist_service:
            logger.warning("Blacklist service not available")
            return False
            
        try:
            # Extract jti from token
            metadata = self.jwt_manager.get_token_metadata(token)
            jti = metadata.get('jti')
            
            if not jti:
                logger.warning("Cannot revoke token: jti not found")
                return False
                
            # Use default blacklist TTL
            blacklist_ttl = 86400  # 24 hours
            
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

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        try:
            jwt_health = {
                "initialized": self._initialized,
                "key_fingerprint": self.jwt_manager.key_fingerprint if self.jwt_manager else None,
            }
            
            blacklist_health = await self.blacklist_service.health_check() if self.blacklist_service else {"status": "unavailable"}
            
            return {
                "status": "healthy" if self._initialized else "degraded",
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
        if not self._initialized or not self.key_manager:
            raise RuntimeError("JWTBackend not properly initialized")
            
        return self.key_manager.get_jwks()