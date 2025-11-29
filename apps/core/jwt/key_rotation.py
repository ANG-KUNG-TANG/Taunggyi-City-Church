import time
import secrets
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from apps.core.cache.async_cache import AsyncRedisCache

logger = logging.getLogger(__name__)

class KeyRotationManager:
    """
    Production-grade JWT Key Rotation Management
    Security Level: CRITICAL
    Responsibilities: Key generation, rotation, lifecycle management
    """
    
    def __init__(self, cache=None, rotation_interval: int = 86400):
        self.cache = cache
        self.rotation_interval = rotation_interval
        self.current_key_id = None
        self.key_pairs: Dict[str, Tuple[str, str]] = {}
        self.key_metadata: Dict[str, Dict] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize key rotation system"""
        if self._initialized:
            return
            
        try:
            if self.cache:
                await self._load_keys_from_cache()
            
            if not self.current_key_id:
                await self._generate_new_key_pair()
                
            self._initialized = True
            logger.info("KeyRotationManager initialized successfully")
            
        except Exception as e:
            logger.critical(f"KeyRotationManager initialization failed: {e}")
            # Generate initial key pair even if cache fails
            await self._generate_new_key_pair()
            self._initialized = True

    async def _load_keys_from_cache(self):
        """Load keys from cache storage"""
        try:
            # Simple cache key since CacheKeyBuilder is not available
            keys_data = await self.cache.get("jwt:keys")
            if keys_data:
                self.key_pairs = keys_data.get('key_pairs', {})
                self.key_metadata = keys_data.get('key_metadata', {})
                self.current_key_id = keys_data.get('current_key_id')
                logger.info(f"Loaded {len(self.key_pairs)} key pairs from cache")
        except Exception as e:
            logger.error(f"Failed to load keys from cache: {e}")

    async def _save_keys_to_cache(self):
        """Save keys to cache storage"""
        try:
            if self.cache:
                keys_data = {
                    'key_pairs': self.key_pairs,
                    'key_metadata': self.key_metadata,
                    'current_key_id': self.current_key_id,
                    'last_updated': datetime.utcnow().isoformat()
                }
                await self.cache.set(
                    "jwt:keys",
                    keys_data,
                    self.rotation_interval * 2
                )
        except Exception as e:
            logger.error(f"Failed to save keys to cache: {e}")

    def _generate_rsa_key_pair(self, key_size: int = 2048) -> Tuple[str, str]:
        """Generate RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
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
        
        return private_pem, public_pem

    async def _generate_new_key_pair(self, key_size: int = 2048) -> str:
        """Generate new RSA key pair and store"""
        private_pem, public_pem = self._generate_rsa_key_pair(key_size)
        key_id = secrets.token_urlsafe(16)
        
        self.key_pairs[key_id] = (private_pem, public_pem)
        self.key_metadata[key_id] = {
            'created_at': datetime.utcnow().isoformat(),
            'key_size': key_size,
            'algorithm': 'RS256',
            'status': 'active'
        }
        self.current_key_id = key_id
        
        await self._save_keys_to_cache()
        logger.info(f"Generated new key pair with ID: {key_id}")
        
        return key_id

    async def rotate_keys(self) -> str:
        """
        Rotate to a new key pair
        Security Level: CRITICAL
        """
        if not self._initialized:
            raise RuntimeError("KeyRotationManager not initialized")
            
        new_key_id = await self._generate_new_key_pair()
        
        # Update previous key status
        for key_id in self.key_pairs:
            if key_id != new_key_id:
                self.key_metadata[key_id]['status'] = 'previous'
        
        # Clean up old keys
        await self._cleanup_old_keys()
        
        logger.info(f"Key rotation completed: new key ID = {new_key_id}")
        return new_key_id

    async def _cleanup_old_keys(self, keep_count: int = 2):
        """
        Remove old keys, keeping specified number
        Security Level: HIGH
        """
        if len(self.key_pairs) <= keep_count:
            return
        
        # Sort keys by creation time and remove oldest
        sorted_keys = sorted(
            self.key_pairs.keys(),
            key=lambda k: self.key_metadata.get(k, {}).get('created_at', ''),
            reverse=True
        )
        
        keys_to_remove = sorted_keys[keep_count:]
        
        for key_id in keys_to_remove:
            if key_id != self.current_key_id:
                del self.key_pairs[key_id]
                del self.key_metadata[key_id]
                logger.info(f"Removed old key: {key_id}")
        
        await self._save_keys_to_cache()

    def get_current_private_key(self) -> Optional[str]:
        """Get current private key"""
        if self.current_key_id and self.current_key_id in self.key_pairs:
            return self.key_pairs[self.current_key_id][0]
        return None

    def get_public_key(self, key_id: str = None) -> Optional[str]:
        """Get public key by ID, or current if not specified"""
        target_key_id = key_id or self.current_key_id
        if target_key_id and target_key_id in self.key_pairs:
            return self.key_pairs[target_key_id][1]
        return None

    def get_all_public_keys(self) -> Dict[str, str]:
        """Get all public keys for verification"""
        return {key_id: key_pair[1] for key_id, key_pair in self.key_pairs.items()}

    def get_jwks(self) -> Dict[str, Any]:
        """
        Get public keys in JWKS format
        Security Level: HIGH
        """
        jwks = {"keys": []}
        
        for key_id, public_pem in self.get_all_public_keys().items():
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            public_key = load_pem_public_key(public_pem.encode(), backend=default_backend())
            
            # Extract RSA public numbers
            public_numbers = public_key.public_numbers()
            
            jwk = {
                "kty": "RSA",
                "use": "sig",
                "kid": key_id,
                "n": self._int_to_base64url(public_numbers.n),
                "e": self._int_to_base64url(public_numbers.e),
                "alg": "RS256"
            }
            
            jwks["keys"].append(jwk)
        
        return jwks

    def _int_to_base64url(self, value: int) -> str:
        """Convert integer to base64url string"""
        import base64
        from math import ceil
        
        # Calculate bytes needed
        byte_length = ceil(value.bit_length() / 8)
        bytes_value = value.to_bytes(byte_length, byteorder='big')
        
        # Convert to base64url
        base64_bytes = base64.urlsafe_b64encode(bytes_value)
        return base64_bytes.decode('ascii').rstrip('=')

    async def get_key_rotation_status(self) -> Dict[str, Any]:
        """Get key rotation status"""
        return {
            "current_key_id": self.current_key_id,
            "total_keys": len(self.key_pairs),
            "rotation_interval": self.rotation_interval,
            "initialized": self._initialized,
            "keys": {
                key_id: {
                    "status": meta.get('status'),
                    "created_at": meta.get('created_at'),
                    "key_size": meta.get('key_size')
                }
                for key_id, meta in self.key_metadata.items()
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for key rotation service"""
        try:
            status = await self.get_key_rotation_status()
            
            return {
                "status": "healthy" if self._initialized and self.current_key_id else "degraded",
                "initialized": self._initialized,
                "current_key_id": self.current_key_id,
                "key_count": len(self.key_pairs),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Key rotation health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }