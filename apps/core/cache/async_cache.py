"""
Production Async Redis Cache with Circuit Breaker & Connection Pooling
Reliability Level: HIGH
"""
import asyncio
import time
from typing import Any, Optional, Dict, List
import logging
from datetime import datetime
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError, ConnectionError

from .cache_keys import CacheKeyBuilder, CacheNamespace
from .serializer import CacheSerializer, SerializationType

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Async circuit breaker for Redis operations"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        
    def can_execute(self) -> bool:
        if self.state == "OPEN":
            if self.last_failure_time and (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True
        
    def on_success(self):
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failures = 0
            
    def on_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.error("Redis circuit breaker OPEN due to consecutive failures")

class AsyncRedisCache:
    """
    Production-grade Async Redis Cache
    Reliability Level: HIGH
    Responsibilities: Connection management, circuit breaker, serialization
    """
    
    def __init__(self, 
                 redis_url: str = 'redis://localhost:6379/0',
                 default_ttl: int = 300,
                 max_connections: int = 20,
                 socket_timeout: int = 5,
                 socket_connect_timeout: int = 5):
        
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        
        self.connection_pool: Optional[ConnectionPool] = None
        self.redis_client: Optional[Redis] = None
        self.serializer = CacheSerializer()
        self.circuit_breaker = CircuitBreaker()
        
        self._metrics = {
            "operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "circuit_breaker_trips": 0,
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "connection_errors": 0
        }
        
        # Don't connect immediately - use lazy connection
        self._is_connected = False

    async def _ensure_connected(self):
        """Ensure Redis connection is established"""
        if self._is_connected and self.redis_client:
            try:
                await self.redis_client.ping()
                return True
            except (ConnectionError, RedisError):
                self._is_connected = False
                self.redis_client = None
                self.connection_pool = None
        
        if not self._is_connected:
            return await self._connect()
        return True

    async def _connect(self) -> bool:
        """Establish connection to Redis"""
        try:
            # Close existing connection if any
            await self._close_connection()
            
            # Create new connection pool
            self.connection_pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=False,  # We handle encoding ourselves
                health_check_interval=30,
                retry_on_timeout=True,
                socket_connect_timeout=self.socket_connect_timeout,
                socket_timeout=self.socket_timeout,
                # Add connection kwargs for better stability
                retry_on_error=[ConnectionError, TimeoutError],
                socket_keepalive=True
            )
            
            # Create Redis client with connection pool
            self.redis_client = Redis.from_pool(self.connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            self._is_connected = True
            
            logger.info(f"Async Redis cache connected successfully to {self.redis_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to Redis {self.redis_url}: {e}")
            self._is_connected = False
            self.redis_client = None
            self.connection_pool = None
            self._metrics["connection_errors"] += 1
            return False

    async def _close_connection(self):
        """Close existing Redis connection"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            if self.connection_pool:
                await self.connection_pool.disconnect()
        except Exception as e:
            logger.debug(f"Error closing old connection: {e}")
        finally:
            self.redis_client = None
            self.connection_pool = None
            self._is_connected = False

    async def _execute_with_circuit_breaker(self, operation: callable, *args, **kwargs) -> Any:
        """Execute Redis operation with circuit breaker protection"""
        if not self.circuit_breaker.can_execute():
            self._metrics["failed_operations"] += 1
            raise RedisError("Circuit breaker is OPEN")
            
        try:
            # Ensure connection before operation
            if not await self._ensure_connected():
                raise ConnectionError("Redis connection unavailable")
                
            result = await operation(*args, **kwargs)
            self.circuit_breaker.on_success()
            self._metrics["successful_operations"] += 1
            return result
            
        except Exception as e:
            self.circuit_breaker.on_failure()
            self._metrics["failed_operations"] += 1
            
            if self.circuit_breaker.state == "OPEN":
                self._metrics["circuit_breaker_trips"] += 1
                logger.critical(f"Redis circuit breaker OPEN after {self.circuit_breaker.failures} failures")
                
            logger.error(f"Redis operation failed: {e}")
            
            # If it's a connection error, mark as disconnected
            if isinstance(e, (ConnectionError, RedisError)):
                self._is_connected = False
                self._metrics["connection_errors"] += 1
                
            raise

    # Core Cache Operations
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        self._metrics["operations"] += 1
        
        async def _get():
            value = await self.redis_client.get(key.encode('utf-8'))
            if value is None:
                self._metrics["misses"] += 1
                return None
            
            self._metrics["hits"] += 1
            return self.serializer.safe_deserialize(value.decode('utf-8'), SerializationType.JSON)
                
        return await self._execute_with_circuit_breaker(_get)

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set value in cache"""
        self._metrics["operations"] += 1
        
        async def _set():
            serialized_value, _ = self.serializer.safe_serialize(value, SerializationType.JSON)
            ttl = expire if expire is not None else self.default_ttl
            
            if ttl:
                result = await self.redis_client.setex(key.encode('utf-8'), ttl, serialized_value.encode('utf-8'))
            else:
                result = await self.redis_client.set(key.encode('utf-8'), serialized_value.encode('utf-8'))
            
            if result:
                self._metrics["sets"] += 1
            return bool(result)
            
        return await self._execute_with_circuit_breaker(_set)

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        self._metrics["operations"] += 1
        
        async def _delete():
            result = await self.redis_client.delete(key.encode('utf-8'))
            success = result > 0
            if success:
                self._metrics["deletes"] += 1
            return success
            
        return await self._execute_with_circuit_breaker(_delete)

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys efficiently"""
        self._metrics["operations"] += 1
        
        async def _get_many():
            encoded_keys = [key.encode('utf-8') for key in keys]
            values = await self.redis_client.mget(encoded_keys)
            
            results = {}
            for key, value in zip(keys, values):
                if value is not None:
                    results[key] = self.serializer.safe_deserialize(value.decode('utf-8'), SerializationType.JSON)
                    self._metrics["hits"] += 1
                else:
                    self._metrics["misses"] += 1
            
            return results
            
        return await self._execute_with_circuit_breaker(_get_many)

    async def flush_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        self._metrics["operations"] += 1
        
        async def _flush_pattern():
            keys = await self.redis_client.keys(pattern.encode('utf-8'))
            if keys:
                await self.redis_client.delete(*keys)
            return len(keys)
            
        return await self._execute_with_circuit_breaker(_flush_pattern)

    # Utility Methods
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        async def _exists():
            return await self.redis_client.exists(key.encode('utf-8')) > 0
        return await self._execute_with_circuit_breaker(_exists)

    async def ttl(self, key: str) -> Optional[int]:
        """Get time to live for key"""
        async def _ttl():
            return await self.redis_client.ttl(key.encode('utf-8'))
        return await self._execute_with_circuit_breaker(_ttl)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        async def _expire():
            return await self.redis_client.expire(key.encode('utf-8'), seconds)
        return await self._execute_with_circuit_breaker(_expire)

    async def incr(self, key: str) -> int:
        """Increment key value"""
        async def _incr():
            return await self.redis_client.incr(key.encode('utf-8'))
        return await self._execute_with_circuit_breaker(_incr)

    # Health & Monitoring
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        try:
            start_time = time.time()
            
            if not await self._ensure_connected():
                return {
                    "status": "unhealthy",
                    "error": "Cannot connect to Redis",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Test basic operations
            test_key = f"health_check_{int(start_time)}"
            test_value = {"timestamp": start_time, "service": "redis"}
            
            set_success = await self.set(test_key, test_value, 10)
            retrieved = await self.get(test_key)
            delete_success = await self.delete(test_key)
            
            latency = time.time() - start_time
            
            # Calculate hit ratio
            total_gets = self._metrics["hits"] + self._metrics["misses"]
            hit_ratio = self._metrics["hits"] / total_gets if total_gets > 0 else 0
            
            success_rate = (self._metrics["successful_operations"] / 
                          self._metrics["operations"] if self._metrics["operations"] > 0 else 0)
            
            return {
                "status": "healthy" if all([set_success, retrieved, delete_success]) else "degraded",
                "latency_ms": round(latency * 1000, 2),
                "circuit_breaker_state": self.circuit_breaker.state,
                "connection_connected": self._is_connected,
                "metrics": {
                    **self._metrics,
                    "hit_ratio": round(hit_ratio, 3),
                    "success_rate": round(success_rate, 3)
                },
                "operations_test": {
                    "set": set_success,
                    "get": retrieved is not None,
                    "delete": delete_success
                }
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "circuit_breaker_state": self.circuit_breaker.state,
                "connection_connected": self._is_connected,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_operations = self._metrics["hits"] + self._metrics["misses"]
        hit_ratio = self._metrics["hits"] / total_operations if total_operations > 0 else 0
        
        success_rate = (self._metrics["successful_operations"] / 
                      self._metrics["operations"] if self._metrics["operations"] > 0 else 0)
        
        return {
            **self._metrics,
            "hit_ratio": round(hit_ratio, 3),
            "success_rate": round(success_rate, 3),
            "default_ttl": self.default_ttl,
            "circuit_breaker_state": self.circuit_breaker.state,
            "connection_connected": self._is_connected,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def close(self):
        """Close Redis connection gracefully"""
        try:
            await self._close_connection()
            logger.info("Async Redis cache connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")

    # Context manager support
    async def __aenter__(self):
        await self._ensure_connected()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Singleton instance for common use
async_redis_cache = AsyncRedisCache()

# Compatibility alias
AsyncCache = AsyncRedisCache