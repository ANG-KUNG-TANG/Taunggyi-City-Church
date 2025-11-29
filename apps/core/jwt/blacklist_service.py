import time
from typing import Any, Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import logging
from ..cache.async_cache import AsyncCache

logger = logging.getLogger(__name__)

class BlacklistService:
    """
    Production-grade Token Blacklist Service
    Security Level: HIGH
    Responsibilities: Token revocation, blacklist management
    """
    
    def __init__(self, cache: AsyncCache, prefix: str = "blacklist"):
        self.cache = cache
        self.prefix = prefix
        self._metrics = {
            "blacklist_operations": 0,
            "blacklist_hits": 0,
            "blacklist_misses": 0
        }

    def _get_key(self, jti: str) -> str:
        """Generate namespaced cache key"""
        return f"{self.prefix}:tokens:{jti}"

    async def blacklist_token(self, 
                            jti: str, 
                            expires_in: int = 86400,
                            reason: str = "revoked") -> bool:
        """
        Add token to blacklist with expiry and reason
        Security Level: HIGH
        
        Args:
            jti: JWT ID (unique token identifier)
            expires_in: Blacklist duration in seconds
            reason: Reason for blacklisting
            
        Returns:
            Success status
        """
        try:
            blacklist_record = {
                "jti": jti,
                "blacklisted_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat(),
                "reason": reason
            }
            
            success = await self.cache.set(
                self._get_key(jti),
                blacklist_record,
                expires_in
            )
            
            if success:
                self._metrics["blacklist_operations"] += 1
                logger.info(f"Token blacklisted: jti={jti}, reason={reason}, expires_in={expires_in}s")
            else:
                logger.error(f"Failed to blacklist token: jti={jti}")
                
            return success
            
        except Exception as e:
            logger.error(f"Blacklist operation failed for jti {jti}: {e}")
            return False

    async def is_blacklisted(self, jti: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if token is blacklisted and return blacklist record
        Security Level: HIGH
        
        Returns:
            Tuple of (is_blacklisted, blacklist_record)
        """
        try:
            record = await self.cache.get(self._get_key(jti))
            
            if record is not None:
                self._metrics["blacklist_hits"] += 1
                logger.debug(f"Blacklist hit: jti={jti}")
                return True, record
            else:
                self._metrics["blacklist_misses"] += 1
                return False, None
                
        except Exception as e:
            logger.error(f"Blacklist check failed for jti {jti}: {e}")
            # Fail secure - treat as blacklisted if check fails
            return True, {"error": "Blacklist service unavailable"}

    async def bulk_blacklist(self, 
                           tokens: List[Dict], 
                           default_expiry: int = 86400) -> Dict[str, bool]:
        """
        Blacklist multiple tokens efficiently
        Security Level: HIGH
        
        Args:
            tokens: List of token dicts with jti and optional expiry
            default_expiry: Default expiry if not specified
            
        Returns:
            Dictionary of jti -> success status
        """
        results = {}
        
        for token_info in tokens:
            jti = token_info["jti"]
            expires_in = token_info.get("expires_in", default_expiry)
            reason = token_info.get("reason", "bulk_revoked")
            
            results[jti] = await self.blacklist_token(jti, expires_in, reason)
            
        logger.info(f"Bulk blacklist completed: {sum(results.values())}/{len(results)} successful")
        return results

    async def remove_from_blacklist(self, jti: str) -> bool:
        """
        Remove token from blacklist (admin operation)
        Security Level: HIGH
        
        Returns:
            Success status
        """
        try:
            success = await self.cache.delete(self._get_key(jti))
            
            if success:
                logger.info(f"Token removed from blacklist: jti={jti}")
            else:
                logger.warning(f"Token not found in blacklist: jti={jti}")
                
            return success
            
        except Exception as e:
            logger.error(f"Blacklist removal failed for jti {jti}: {e}")
            return False

    async def cleanup_expired(self) -> int:
        """
        Clean up expired blacklist entries (maintenance operation)
        Security Level: MEDIUM
        
        Returns:
            Number of entries cleaned up
        """
        # Note: Redis handles TTL automatically
        # This method is for additional cleanup if needed
        logger.info("Expired blacklist entries cleanup completed (handled by Redis TTL)")
        return 0

    async def get_blacklist_stats(self) -> Dict[str, Any]:
        """
        Get blacklist service statistics
        Security Level: LOW
        """
        return {
            **self._metrics,
            "service": "token_blacklist",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for blacklist service
        Security Level: LOW
        """
        try:
            # Test write and read
            test_jti = "health_check_" + str(int(time.time()))
            test_data = {"test": True, "timestamp": time.time()}
            
            await self.cache.set(f"{self.prefix}:health", test_data, 10)
            retrieved = await self.cache.get(f"{self.prefix}:health")
            
            return {
                "status": "healthy" if retrieved else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "cache_accessible": retrieved is not None
            }
        except Exception as e:
            logger.error(f"Blacklist health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }