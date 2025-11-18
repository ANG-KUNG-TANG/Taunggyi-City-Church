"""
Production-level JWT Token Manager with RSA256 signing
Security Level: CRITICAL
Compliance: RFC 7519, OWASP JWT Guidelines
"""
import jwt
import time
import uuid
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes, PublicKeyTypes

logger = logging.getLogger(__name__)

class TokenType(Enum):
    """JWT Token types with specific security contexts"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"

@dataclass(frozen=True)
class TokenConfig:
    """Immutable token configuration"""
    access_token_expiry: int = 900  # 15 minutes
    refresh_token_expiry: int = 604800  # 7 days
    reset_token_expiry: int = 1800  # 30 minutes
    algorithm: str = "RS256"
    issuer: str = "auth-service"
    audience: List[str] = None

    def __post_init__(self):
        if self.audience is None:
            object.__setattr__(self, 'audience', ["api"])

@dataclass(frozen=True)
class TokenPayload:
    """Immutable token payload structure"""
    user_id: str
    email: str
    token_type: TokenType
    exp: datetime
    iat: datetime
    jti: str
    roles: List[str] = None
    permissions: List[str] = None
    session_id: str = None

    def to_claims(self) -> Dict[str, Any]:
        """Convert to JWT claims dictionary"""
        claims = {
            "sub": self.user_id,
            "email": self.email,
            "token_type": self.token_type.value,
            "exp": int(self.exp.timestamp()),
            "iat": int(self.iat.timestamp()),
            "jti": self.jti,
            "iss": "auth-service",
            "aud": ["api"]
        }
        
        if self.roles:
            claims["roles"] = self.roles
        if self.permissions:
            claims["permissions"] = self.permissions
        if self.session_id:
            claims["session_id"] = self.session_id
            
        return claims

class JWTManager:
    """
    Production-grade JWT Token Manager
    Security Level: CRITICAL
    Responsibilities: Token creation, validation, and cryptographic operations
    """
    
    def __init__(self, config: TokenConfig, private_key: str, public_key: str):
        """
        Initialize JWT Manager
        
        Args:
            config: Token configuration
            private_key: RSA private key in PEM format
            public_key: RSA public key in PEM format
            
        Raises:
            ValueError: Invalid keys or configuration
            CryptographyError: Key loading failure
        """
        self.config = config
        self._private_key = self._load_and_validate_private_key(private_key)
        self._public_key = self._load_and_validate_public_key(public_key)
        self._key_fingerprint = self._generate_key_fingerprint(public_key)
        
        logger.info(f"JWT Manager initialized with key fingerprint: {self._key_fingerprint}")

    def _load_and_validate_private_key(self, key_data: str) -> PrivateKeyTypes:
        """
        Load and validate RSA private key
        Security Level: CRITICAL
        """
        try:
            if isinstance(key_data, str):
                key_data = key_data.encode('utf-8')
                
            private_key = serialization.load_pem_private_key(
                key_data,
                password=None,
                backend=default_backend()
            )
            
            # Validate key type and size
            if not isinstance(private_key, rsa.RSAPrivateKey):
                raise ValueError("Private key must be RSA type")
                
            if private_key.key_size < 2048:
                raise ValueError("RSA key size must be at least 2048 bits")
                
            return private_key
            
        except Exception as e:
            logger.critical(f"Private key loading failed: {e}")
            raise

    def _load_and_validate_public_key(self, key_data: str) -> PublicKeyTypes:
        """
        Load and validate RSA public key
        Security Level: CRITICAL
        """
        try:
            if isinstance(key_data, str):
                key_data = key_data.encode('utf-8')
                
            public_key = serialization.load_pem_public_key(
                key_data,
                backend=default_backend()
            )
            
            if not isinstance(public_key, rsa.RSAPublicKey):
                raise ValueError("Public key must be RSA type")
                
            return public_key
            
        except Exception as e:
            logger.critical(f"Public key loading failed: {e}")
            raise

    def _generate_key_fingerprint(self, public_key: str) -> str:
        """Generate SHA256 fingerprint of public key"""
        import hashlib
        key_bytes = public_key.encode('utf-8') if isinstance(public_key, str) else public_key
        return hashlib.sha256(key_bytes).hexdigest()[:16]

    def create_access_token(self, 
                          user_id: str, 
                          email: str,
                          roles: List[str] = None,
                          permissions: List[str] = None,
                          session_id: str = None) -> str:
        """
        Create access token with short expiry
        Security Level: HIGH
        Compliance: OWASP JWT Cheat Sheet
        
        Args:
            user_id: Unique user identifier
            email: User email address
            roles: User roles
            permissions: User permissions
            session_id: Session identifier
            
        Returns:
            Signed JWT token string
            
        Raises:
            jwt.PyJWTError: Token creation failed
        """
        return self._create_token(
            user_id=user_id,
            email=email,
            token_type=TokenType.ACCESS,
            expiry_seconds=self.config.access_token_expiry,
            roles=roles,
            permissions=permissions,
            session_id=session_id
        )

    def create_refresh_token(self, user_id: str, email: str, session_id: str = None) -> str:
        """
        Create refresh token with longer expiry
        Security Level: HIGH
        """
        return self._create_token(
            user_id=user_id,
            email=email,
            token_type=TokenType.REFRESH,
            expiry_seconds=self.config.refresh_token_expiry,
            session_id=session_id
        )

    def create_reset_token(self, user_id: str, email: str) -> str:
        """
        Create password reset token
        Security Level: HIGH
        """
        return self._create_token(
            user_id=user_id,
            email=email,
            token_type=TokenType.RESET_PASSWORD,
            expiry_seconds=self.config.reset_token_expiry
        )

    def _create_token(self,
                     user_id: str,
                     email: str,
                     token_type: TokenType,
                     expiry_seconds: int,
                     roles: List[str] = None,
                     permissions: List[str] = None,
                     session_id: str = None) -> str:
        """
        Core token creation method
        Security Level: CRITICAL
        """
        try:
            now = datetime.utcnow()
            exp = now + timedelta(seconds=expiry_seconds)
            jti = str(uuid.uuid4())

            payload = TokenPayload(
                user_id=user_id,
                email=email,
                token_type=token_type,
                exp=exp,
                iat=now,
                jti=jti,
                roles=roles,
                permissions=permissions,
                session_id=session_id
            )

            token = jwt.encode(
                payload.to_claims(),
                self._private_key,
                algorithm=self.config.algorithm
            )

            logger.info(f"Token created: type={token_type.value}, jti={jti}, user={user_id}")
            return token

        except Exception as e:
            logger.error(f"Token creation failed for user {user_id}: {e}")
            raise

    def verify_token(self, token: str, token_type: TokenType = None) -> Tuple[bool, Optional[Dict]]:
        """
        Verify JWT token signature and claims
        Security Level: CRITICAL
        Compliance: RFC 7519 Section 7.2
        
        Args:
            token: JWT token string
            token_type: Expected token type for validation
            
        Returns:
            Tuple of (is_valid, payload)
        """
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=[self.config.algorithm],
                issuer=self.config.issuer,
                audience=self.config.audience,
                options={"require": ["exp", "iat", "sub", "jti"]}
            )
            
            # Validate token type if specified
            if token_type and payload.get("token_type") != token_type.value:
                logger.warning(f"Token type mismatch: expected {token_type.value}, got {payload.get('token_type')}")
                return False, None
            
            # Validate expiration with leeway
            current_time = time.time()
            if payload.get("exp", 0) < current_time:
                logger.warning("Token expired")
                return False, None
                
            # Validate issued at time
            if payload.get("iat", 0) > current_time + 60:  # 60s leeway for clock skew
                logger.warning("Token issued in future")
                return False, None
                
            logger.debug(f"Token verified: jti={payload.get('jti')}, user={payload.get('sub')}")
            return True, payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired during verification")
            return False, None
        except jwt.InvalidIssuerError:
            logger.warning("Invalid token issuer")
            return False, None
        except jwt.InvalidAudienceError:
            logger.warning("Invalid token audience")
            return False, None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return False, None

    def get_token_metadata(self, token: str) -> Dict[str, Any]:
        """
        Extract token metadata without verification
        Security Level: LOW (for debugging/monitoring only)
        
        Returns:
            Token metadata for logging and monitoring
        """
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return {
                "jti": payload.get("jti"),
                "user_id": payload.get("sub"),
                "token_type": payload.get("token_type"),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0)),
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
                "roles": payload.get("roles", []),
                "session_id": payload.get("session_id")
            }
        except Exception as e:
            logger.warning(f"Failed to extract token metadata: {e}")
            return {}

    @property
    def public_key_pem(self) -> str:
        """Get public key in PEM format"""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    @property
    def key_fingerprint(self) -> str:
        """Get public key fingerprint"""
        return self._key_fingerprint