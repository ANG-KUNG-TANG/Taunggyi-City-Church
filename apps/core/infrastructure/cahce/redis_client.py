"""
Production Redis Client with Connection Pooling and Circuit Breaker
Reliability Level: HIGH
Compliance: Redis Best Practices, Circuit Breaker Pattern
"""
import time
import redis.asyncio as redis
from typing import Any, Optional, Dict, List, Union
import logging
import asyncio
from datetime import datetime
from core.cache.async_cache import AsyncCache
from core.cache.serializer import CacheSerializer, SerializationType

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Circuit Breaker for Redis operations
    Reliability Level: HIGH
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if self.state == "OPEN":
            if (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True
        
    def on_success(self):
        """Handle successful operation"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failures = 0
            
    def on_failure(self):
        """Handle failed operation"""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.error("Circuit breaker OPEN due to consecutive failures")

class RedisClient(AsyncCache):
    """
    Production-grade Async Redis Client
    Reliability Level: HIGH
    Responsibilities: Connection management, serialization, error handling
    """
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 6379,
                 db: int = 0,
                 password: str = None,
                 max_connections: int = 20,
                 socket_timeout: int = 5,
                 socket_connect_timeout: int = 5,
                 retry_on_timeout: bool = True,
                 health_check_interval: int = 30):
        
        self.connection_pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
            decode_responses=False,  # Handle encoding manually
            health_check_interval=health_check_interval
        )
        
        self.client = redis.Redis(connection_pool=self.connection_pool)
        self.circuit_breaker = CircuitBreaker()
        self._metrics = {
            "operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "circuit_breaker_trips": 0
        }

    async def _execute_with_circuit_breaker(self, operation: callable, *args, **kwargs) -> Any:
        """
        Execute Redis operation with circuit breaker protection
        Reliability Level: HIGH
        """
        if not self.circuit_breaker.can_execute():
            self._metrics["failed_operations"] += 1
            raise redis.RedisError("Circuit breaker is OPEN")
            
        try:
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
            raise

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _get():
            value = await self.client.get(key)
            if value is None:
                return None
            return CacheSerializer.deserialize(value.decode('utf-8'), SerializationType.JSON)
            
        return await self._execute_with_circuit_breaker(_get)

    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in Redis with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _set():
            serialized_value = CacheSerializer.serialize(
                value, 
                CacheSerializer.detect_serialization_method(value)
            )
            
            if expire:
                return await self.client.setex(key, expire, serialized_value)
            else:
                return await self.client.set(key, serialized_value)
                
        result = await self._execute_with_circuit_breaker(_set)
        return bool(result)

    async def delete(self, key: str) -> bool:
        """Delete key from Redis with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _delete():
            return await self.client.delete(key)
            
        result = await self._execute_with_circuit_breaker(_delete)
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _exists():
            return await self.client.exists(key) > 0
            
        return await self._execute_with_circuit_breaker(_exists)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiry with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _expire():
            return await self.client.expire(key, seconds)
            
        return await self._execute_with_circuit_breaker(_expire)

    async def ttl(self, key: str) -> int:
        """Get time to live for key with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _ttl():
            return await self.client.ttl(key)
            
        return await self._execute_with_circuit_breaker(_ttl)

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment value with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _incr():
            if amount == 1:
                return await self.client.incr(key)
            else:
                return await self.client.incrby(key, amount)
                
        return await self._execute_with_circuit_breaker(_incr)

    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement value with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _decr():
            if amount == 1:
                return await self.client.decr(key)
            else:
                return await self.client.decrby(key, amount)
                
        return await self._execute_with_circuit_breaker(_decr)

    async def flush_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _flush_pattern():
            keys = await self.client.keys(pattern)
            if keys:
                return await self.client.delete(*keys)
            return 0
            
        return await self._execute_with_circuit_breaker(_flush_pattern)

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _get_many():
            values = await self.client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = CacheSerializer.deserialize(value.decode('utf-8'), SerializationType.JSON)
                    except:
                        result[key] = value.decode('utf-8')
            return result
            
        return await self._execute_with_circuit_breaker(_get_many)

    async def set_many(self, data: Dict[str, Any], expire: int = None) -> bool:
        """Set multiple values with circuit breaker"""
        self._metrics["operations"] += 1
        
        async def _set_many():
            pipeline = self.client.pipeline()
            
            for key, value in data.items():
                serialized_value = CacheSerializer.serialize(
                    value,
                    CacheSerializer.detect_serialization_method(value)
                )
                if expire:
                    pipeline.setex(key, expire, serialized_value)
                else:
                    pipeline.set(key, serialized_value)
            
            await pipeline.execute()
            return True
            
        return await self._execute_with_circuit_breaker(_set_many)

    def get_pipeline(self):
        """Get Redis pipeline for batch operations"""
        return self.client.pipeline()

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        try:
            start_time = time.time()
            
            # Test connection and basic operations
            await self.client.ping()
            test_key = f"health_check_{int(start_time)}"
            test_value = {"timestamp": start_time, "service": "redis"}
            
            await self.set(test_key, test_value, 10)
            retrieved = await self.get(test_key)
            await self.delete(test_key)
            
            latency = time.time() - start_time
            
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "circuit_breaker_state": self.circuit_breaker.state,
                "connection_pool": {
                    "max_connections": self.connection_pool.max_connections,
                    "connected_clients": len(self.connection_pool._connections) if hasattr(self.connection_pool, '_connections') else 'unknown'
                },
                "metrics": self._metrics
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "circuit_breaker_state": self.circuit_breaker.state,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def close(self):
        """Graceful shutdown"""
        try:
            await self.client.close()
            await self.connection_pool.disconnect()
            logger.info("Redis client connections closed gracefully")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")

    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance and operational metrics"""
        return {
            **self._metrics,
            "circuit_breaker": {
                "state": self.circuit_breaker.state,
                "failures": self.circuit_breaker.failures,
                "last_failure": self.circuit_breaker.last_failure_time.isoformat() if self.circuit_breaker.last_failure_time else None
            },
            "timestamp": datetime.utcnow().isoformat()
        }