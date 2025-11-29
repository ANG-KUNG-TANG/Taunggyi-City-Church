from datetime import datetime
import time
import asyncio
from typing import Any, Optional, Dict, Tuple, List
from dataclasses import dataclass
from enum import Enum
import logging
from ..cache.async_cache import AsyncCache

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"

@dataclass(frozen=True)
class RateLimitConfig:
    """Immutable rate limit configuration"""
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    max_requests: int = 100
    window_seconds: int = 3600
    block_duration: int = 300  # Additional block after limit exceeded

class RateLimitResult:
    """Rate limit check result"""
    
    def __init__(self, allowed: bool, config: RateLimitConfig, details: Dict):
        self.allowed = allowed
        self.config = config
        self.details = details
        
    @property
    def limit(self) -> int:
        return self.details.get("limit", 0)
        
    @property
    def remaining(self) -> int:
        return self.details.get("remaining", 0)
        
    @property
    def reset_time(self) -> int:
        return self.details.get("reset_time", 0)
        
    @property
    def retry_after(self) -> int:
        if self.allowed:
            return 0
        return max(0, self.reset_time - int(time.time()))

class RateLimiter:
    """
    Production-grade Rate Limiter
    Security Level: HIGH
    Responsibilities: Request rate limiting, abuse prevention
    """
    
    def __init__(self, cache: AsyncCache, prefix: str = "rate_limit"):
        self.cache = cache
        self.prefix = prefix
        self._metrics = {
            "checks": 0,
            "allowed": 0,
            "denied": 0,
            "errors": 0
        }

    def _get_key(self, identifier: str, action: str) -> str:
        """Generate rate limit key"""
        return f"{self.prefix}:{action}:{identifier}"

    async def check_rate_limit(self, 
                             identifier: str, 
                             action: str, 
                             config: RateLimitConfig) -> RateLimitResult:
        """
        Check rate limit for identifier and action
        Security Level: HIGH
        """
        self._metrics["checks"] += 1
        
        try:
            if config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return await self._sliding_window_check(identifier, action, config)
            else:
                # Fallback to sliding window for unsupported strategies
                logger.warning(f"Unsupported strategy {config.strategy}, using sliding window")
                return await self._sliding_window_check(identifier, action, config)
                
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Rate limit check failed for {identifier}/{action}: {e}")
            # Fail open in case of errors to avoid blocking legitimate traffic
            return RateLimitResult(True, config, {"error": "Rate limit service unavailable"})

    async def _sliding_window_check(self, 
                                  identifier: str, 
                                  action: str, 
                                  config: RateLimitConfig) -> RateLimitResult:
        """
        Sliding window rate limit implementation
        Security Level: HIGH
        """
        key = self._get_key(identifier, action)
        now = time.time()
        window_start = now - config.window_seconds
        
        try:
            # Get current requests in window
            current_requests = await self._get_current_requests(key, window_start)
            
            # Add current request if under limit
            if current_requests < config.max_requests:
                await self._add_request(key, now, config.window_seconds)
                current_requests += 1
                self._metrics["allowed"] += 1
                allowed = True
            else:
                self._metrics["denied"] += 1
                allowed = False
                logger.warning(f"Rate limit exceeded: {identifier}/{action}, requests={current_requests}")
            
            remaining = max(0, config.max_requests - current_requests)
            reset_time = int(now + config.window_seconds)
            
            details = {
                "limit": config.max_requests,
                "remaining": remaining,
                "reset_time": reset_time,
                "window_seconds": config.window_seconds,
                "current_requests": current_requests,
                "strategy": config.strategy.value
            }
            
            return RateLimitResult(allowed, config, details)
            
        except Exception as e:
            logger.error(f"Sliding window check failed: {e}")
            raise

    async def _get_current_requests(self, key: str, window_start: float) -> int:
        """Get number of requests in current window"""
        # This is a simplified implementation
        # In production, you might use Redis sorted sets
        window_data = await self.cache.get(key)
        if not window_data:
            return 0
        
        requests = window_data.get("requests", [])
        # Filter requests within current window
        valid_requests = [ts for ts in requests if ts >= window_start]
        return len(valid_requests)

    async def _add_request(self, key: str, timestamp: float, window_seconds: int):
        """Add request to rate limit window"""
        window_data = await self.cache.get(key) or {"requests": []}
        window_data["requests"].append(timestamp)
        
        # Keep only recent requests to prevent memory issues
        window_start = timestamp - window_seconds
        window_data["requests"] = [ts for ts in window_data["requests"] if ts >= window_start]
        
        await self.cache.set(key, window_data, window_seconds)

    async def get_rate_limit_info(self, 
                                identifier: str, 
                                action: str, 
                                config: RateLimitConfig) -> Dict[str, Any]:
        """
        Get current rate limit information without consuming a request
        Security Level: MEDIUM
        """
        try:
            key = self._get_key(identifier, action)
            now = time.time()
            window_start = now - config.window_seconds
            
            current_requests = await self._get_current_requests(key, window_start)
            
            return {
                "limit": config.max_requests,
                "remaining": max(0, config.max_requests - current_requests),
                "reset_time": int(now + config.window_seconds),
                "current_requests": current_requests,
                "window_seconds": config.window_seconds
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {"error": "Service unavailable"}

    async def reset_rate_limit(self, identifier: str, action: str) -> bool:
        """
        Reset rate limit for identifier and action (admin operation)
        Security Level: HIGH
        """
        try:
            key = self._get_key(identifier, action)
            success = await self.cache.delete(key)
                
            logger.info(f"Rate limit reset: {identifier}/{action}")
            return success
        except Exception as e:
            logger.error(f"Rate limit reset failed: {e}")
            return False

    async def get_global_stats(self) -> Dict[str, Any]:
        """
        Get global rate limiting statistics
        Security Level: LOW
        """
        return {
            **self._metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "rate_limiter"
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for rate limiter
        Security Level: LOW
        """
        try:
            test_config = RateLimitConfig(max_requests=10, window_seconds=10)
            result = await self.check_rate_limit("health_check", "test", test_config)
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "check_result": result.allowed
            }
        except Exception as e:
            logger.error(f"Rate limiter health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }