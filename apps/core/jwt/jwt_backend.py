import os
import uuid
import secrets
from typing import Optional, Tuple, Dict, Any, List
import logging
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import jwt
from enum import Enum

logger = logging.getLogger(__name__)

class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"

class TokenConfig:
    """JWT Configuration"""
    
    def __init__(
        self,
        access_token_expiry: int = 900,  # 15 minutes
        refresh_token_expiry: int = 604800,  # 7 days
        reset_token_expiry: int = 1800,  # 30 minutes
        algorithm: str = "RS256",
        issuer: str = "auth-service",
        audience: List[str] = None
    ):
        self.access_token_expiry = access_token_expiry
        self.refresh_token_expiry = refresh_token_expiry
        self.reset_token_expiry = reset_token_expiry
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience or ["api"]

class JWTManager:
    """
    Core JWT Token Management
    Security Level: CRITICAL
    """
    
    def __init__(self, config: TokenConfig, private_key: str, public_key: str):
        self.config = config
        self.private_key = private_key
        self.public_key = public_key
        self.key_fingerprint = self._generate_key_fingerprint(public_key)
    
    def _generate_key_fingerprint(self, public_key: str) -> str:
        """Generate fingerprint for key identification"""
        import hashlib
        return hashlib.sha256(public_key.encode()).hexdigest()[:16]
    
    def create_access_token(
        self, 
        user_id: str,
        email: str,
        roles: List[str] = None,
        permissions: List[str] = None,
        session_id: str = None
    ) -> str:
        """Create access token with enhanced security claims"""
        now = datetime.utcnow()
        expires = now + timedelta(seconds=self.config.access_token_expiry)
        
        payload = {
            "token_type": TokenType.ACCESS.value,
            "sub": user_id,
            "email": email,
            "roles": roles or [],
            "permissions": permissions or [],
            "session_id": session_id or str(uuid.uuid4()),
            "jti": secrets.token_urlsafe(32),  # Unique token ID
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "version": "1.0"
        }
        
        return jwt.encode(
            payload, 
            self.private_key, 
            algorithm=self.config.algorithm
        )
    
    def create_refresh_token(self, user_id: str, email: str, session_id: str = None) -> str:
        """Create refresh token with limited claims"""
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
            "aud": self.config.audience
        }
        
        return jwt.encode(
            payload, 
            self.private_key, 
            algorithm=self.config.algorithm
        )
    
    def create_reset_token(self, user_id: str, email: str) -> str:
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
            "aud": self.config.audience,
            "purpose": "password_reset"
        }
        
        return jwt.encode(
            payload, 
            self.private_key, 
            algorithm=self.config.algorithm
        )
    
    def verify_token(self, token: str, token_type: TokenType = None) -> Tuple[bool, Optional[Dict]]:
        """Comprehensive token verification"""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.public_key,
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
    
    def get_token_metadata(self, token: str) -> Dict[str, Any]:
        """Extract token metadata without verification"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return {
                "jti": payload.get("jti"),
                "sub": payload.get("sub"),
                "token_type": payload.get("token_type"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat"),
                "session_id": payload.get("session_id")
            }
        except Exception as e:
            logger.error(f"Failed to extract token metadata: {e}")
            return {}

class JWTBackend:
    """
    Production-grade JWT Backend Service
    Security Level: CRITICAL
    """
    
    _instance: Optional['JWTBackend'] = None
    
    def __init__(self, cache=None, config: TokenConfig = None):
        if JWTBackend._instance is not None:
            raise RuntimeError("JWTBackend is a singleton! Use get_instance()")
        
        self.cache = cache
        self.config = config or self._load_config_from_env()
        self.key_manager = None
        self.jwt_manager = None
        self.blacklist_service = None
        self._initialized = False
        
        # Import here to avoid circular imports
        try:
            from .key_rotation import KeyRotationManager
            from .blacklist_service import BlacklistService
            self.key_manager = KeyRotationManager(cache) if cache else None
            self.blacklist_service = BlacklistService(cache) if cache else None
        except ImportError as e:
            logger.warning(f"Could not import security services: {e}")
        
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
                current_private_key = self.key_manager.get_current_private_key()
                current_public_key = self.key_manager.get_public_key()
                
                if current_private_key and current_public_key:
                    self.jwt_manager = JWTManager(
                        config=self.config,
                        private_key=current_private_key,
                        public_key=current_public_key
                    )
                    logger.info("JWTBackend initialized with RSA key rotation")
                else:
                    # Fallback to generated RSA keys
                    logger.warning("Key rotation not available, generating temporary RSA keys")
                    self.jwt_manager = self._create_rsa_manager()
            else:
                # No cache, use generated RSA keys
                self.jwt_manager = self._create_rsa_manager()
                logger.info("JWTBackend initialized with generated RSA keys")
            
            self._initialized = True
            logger.info("JWTBackend initialized successfully")
            
        except Exception as e:
            logger.critical(f"JWTBackend initialization failed: {e}")
            # Final fallback
            self.jwt_manager = self._create_rsa_manager()
            self._initialized = True

    def _create_rsa_manager(self) -> JWTManager:
        """Create RSA JWT manager as fallback"""
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
        
        # Ensure algorithm matches key type
        rsa_config = TokenConfig(
            access_token_expiry=self.config.access_token_expiry,
            refresh_token_expiry=self.config.refresh_token_expiry,
            reset_token_expiry=self.config.reset_token_expiry,
            algorithm="RS256",  # Must be RS256 for RSA keys
            issuer=self.config.issuer,
            audience=self.config.audience
        )
        
        return JWTManager(
            config=rsa_config,
            private_key=private_pem,
            public_key=public_pem
        )

    def _load_config_from_env(self) -> TokenConfig:
        """Load configuration from environment variables"""
        return TokenConfig(
            access_token_expiry=int(os.getenv('JWT_ACCESS_EXPIRY', 900)),
            refresh_token_expiry=int(os.getenv('JWT_REFRESH_EXPIRY', 604800)),
            reset_token_expiry=int(os.getenv('JWT_RESET_EXPIRY', 1800)),
            algorithm=os.getenv('JWT_ALGORITHM', 'RS256'),  # Default to RS256
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
            # Verify token signature and claims
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
            
            # Check token type validity
            token_type = payload.get('token_type')
            valid_types = [t.value for t in TokenType]
            if token_type not in valid_types:
                logger.warning(f"Invalid token type: {token_type}")
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
                
            # Calculate blacklist TTL based on token expiration
            exp_timestamp = metadata.get('exp')
            if exp_timestamp:
                exp_time = datetime.fromtimestamp(exp_timestamp)
                ttl = max(0, int((exp_time - datetime.utcnow()).total_seconds()))
            else:
                ttl = 86400  # Default 24 hours
            
            success = await self.blacklist_service.blacklist_token(
                jti=jti,
                expires_in=ttl,
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

    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using valid refresh token
        Security Level: HIGH
        """
        try:
            # Verify refresh token
            is_valid, payload = await self.verify_token(refresh_token, TokenType.REFRESH)
            if not is_valid:
                raise ValueError("Invalid refresh token")
            
            # Create new tokens
            return await self.create_tokens(
                user_id=payload['sub'],
                email=payload['email'],
                roles=payload.get('roles', []),
                permissions=payload.get('permissions', []),
                session_id=payload.get('session_id')
            )
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise

    async def create_reset_token(self, user_id: str, email: str) -> str:
        """Create password reset token"""
        if not self._initialized:
            await self.initialize()
            
        return self.jwt_manager.create_reset_token(user_id, email)

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        try:
            jwt_health = {
                "initialized": self._initialized,
                "algorithm": self.config.algorithm,
                "key_fingerprint": self.jwt_manager.key_fingerprint if self.jwt_manager else None,
            }
            
            key_rotation_health = await self.key_manager.health_check() if self.key_manager else {"status": "unavailable"}
            blacklist_health = await self.blacklist_service.health_check() if self.blacklist_service else {"status": "unavailable"}
            
            return {
                "status": "healthy" if self._initialized else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "jwt_backend": jwt_health,
                "key_rotation": key_rotation_health,
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