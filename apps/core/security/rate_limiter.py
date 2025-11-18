"""
Production Rate Limiter with Sliding Window Algorithm
Security Level: HIGH
Compliance: OWASP Rate Limiting
"""
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
    TOKEN_BUCKET = "token_bucket"

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

    def _get_key(self, identifier: str, action: str, strategy: RateLimitStrategy) -> str:
        """Generate rate limit key"""
        return f"{self.prefix}:{strategy.value}:{action}:{identifier}"

    async def check_rate_limit(self, 
                             identifier: str, 
                             action: str, 
                             config: RateLimitConfig) -> RateLimitResult:
        """
        Check rate limit for identifier and action
        Security Level: HIGH
        
        Args:
            identifier: Client identifier (IP, user ID, etc.)
            action: Action being limited (login, api_call, etc.)
            config: Rate limit configuration
            
        Returns:
            RateLimitResult with decision and details
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
        Algorithm: Sorted set with timestamp scores
        """
        key = self._get_key(identifier, action, config.strategy)
        now = time.time()
        window_start = now - config.window_seconds
        
        try:
            # Use Redis sorted set for efficient window management
            pipeline = self.cache.get_pipeline()
            
            # Remove expired requests
            pipeline.zremrangebyscore(key, 0, window_start)
            
            # Count current window requests
            pipeline.zcard(key)
            
            # Add current request
            pipeline.zadd(key, {str(now): now})
            
            # Set expiry
            pipeline.expire(key, config.window_seconds)
            
            results = await pipeline.execute()
            
            current_requests = results[1] if len(results) > 1 else 0
            remaining = max(0, config.max_requests - current_requests)
            reset_time = int(now + config.window_seconds)
            
            allowed = current_requests < config.max_requests
            
            if allowed:
                self._metrics["allowed"] += 1
            else:
                self._metrics["denied"] += 1
                logger.warning(f"Rate limit exceeded: {identifier}/{action}, requests={current_requests}")
            
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

    async def get_rate_limit_info(self, 
                                identifier: str, 
                                action: str, 
                                config: RateLimitConfig) -> Dict[str, Any]:
        """
        Get current rate limit information without consuming a request
        Security Level: MEDIUM
        """
        try:
            key = self._get_key(identifier, action, config.strategy)
            now = time.time()
            window_start = now - config.window_seconds
            
            pipeline = self.cache.get_pipeline()
            pipeline.zremrangebyscore(key, 0, window_start)
            pipeline.zcard(key)
            pipeline.zrange(key, 0, -1, withscores=True)
            
            results = await pipeline.execute()
            
            current_requests = results[1] if len(results) > 1 else 0
            request_timestamps = results[2] if len(results) > 2 else []
            
            return {
                "limit": config.max_requests,
                "remaining": max(0, config.max_requests - current_requests),
                "reset_time": int(now + config.window_seconds),
                "current_requests": current_requests,
                "window_seconds": config.window_seconds,
                "request_timestamps": request_timestamps
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
            # Reset for all strategies
            for strategy in RateLimitStrategy:
                key = self._get_key(identifier, action, strategy)
                await self.cache.delete(key)
                
            logger.info(f"Rate limit reset: {identifier}/{action}")
            return True
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