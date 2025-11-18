from typing import Optional
from dataclasses import dataclass
from enum import Enum

class CacheNamespace(Enum):
    USER = "user"
    SESSION = "session"
    RATE_LIMIT = "rate_limit"
    BLACKLIST = "blacklist"
    CONFIG = "config"

@dataclass
class CacheKeyBuilder:
    """Centralized cache key management"""
    
    @staticmethod
    def build_key(namespace: CacheNamespace, *parts: str, version: Optional[str] = None) -> str:
        """Build cache key with namespace and versioning"""
        key_parts = [namespace.value] + list(parts)
        key = ":".join(str(part) for part in key_parts if part is not None)
        
        if version:
            key = f"{key}:v{version}"
            
        return key
    
    # User-related keys
    @staticmethod
    def user_profile(user_id: str, version: str = "1") -> str:
        return CacheKeyBuilder.build_key(CacheNamespace.USER, "profile", user_id, version=version)
    
    @staticmethod
    def user_sessions(user_id: str, version: str = "1") -> str:
        return CacheKeyBuilder.build_key(CacheNamespace.USER, "sessions", user_id, version=version)
    
    @staticmethod
    def user_by_email(email: str, version: str = "1") -> str:
        return CacheKeyBuilder.build_key(CacheNamespace.USER, "email", email, version=version)
    
    # Session keys
    @staticmethod
    def session_token(token_id: str, version: str = "1") -> str:
        return CacheKeyBuilder.build_key(CacheNamespace.SESSION, "token", token_id, version=version)
    
    # Rate limit keys
    @staticmethod
    def rate_limit(identifier: str, action: str, version: str = "1") -> str:
        return CacheKeyBuilder.build_key(CacheNamespace.RATE_LIMIT, action, identifier, version=version)
    
    # Blacklist keys
    @staticmethod
    def blacklist_token(jti: str, version: str = "1") -> str:
        return CacheKeyBuilder.build_key(CacheNamespace.BLACKLIST, "token", jti, version=version)
    
    # Configuration keys
    @staticmethod
    def config_jwt_keys(version: str = "1") -> str:
        return CacheKeyBuilder.build_key(CacheNamespace.CONFIG, "jwt_keys", version=version)