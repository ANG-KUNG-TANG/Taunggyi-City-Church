"""
Production Redis Client with Connection Pooling and Circuit Breaker
Reliability Level: HIGH
Compliance: Redis Best Practices, Circuit Breaker Pattern
"""
import time
import redis
from typing import Any, Optional, Dict, List, Union
import logging
import asyncio
from datetime import datetime

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
            if self.last_failure_time and (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout:
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

class RedisClient:
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
            decode_responses=True,  # Handle encoding automatically
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

    def _execute_with_circuit_breaker(self, operation: callable, *args, **kwargs) -> Any:
        """
        Execute Redis operation with circuit breaker protection
        Reliability Level: HIGH
        """
        if not self.circuit_breaker.can_execute():
            self._metrics["failed_operations"] += 1
            raise redis.RedisError("Circuit breaker is OPEN")
            
        try:
            result = operation(*args, **kwargs)
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

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with circuit breaker"""
        self._metrics["operations"] += 1
        
        def _get():
            value = self.client.get(key)
            if value is None:
                return None
            try:
                import json
                return json.loads(value)
            except:
                return value
                
        return self._execute_with_circuit_breaker(_get)

    def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in Redis with circuit breaker"""
        self._metrics["operations"] += 1
        
        def _set():
            import json
            try:
                serialized_value = json.dumps(value)
            except:
                serialized_value = str(value)
            
            if expire:
                return self.client.setex(key, expire, serialized_value)
            else:
                return self.client.set(key, serialized_value)
                
        result = self._execute_with_circuit_breaker(_set)
        return bool(result)

    def delete(self, key: str) -> bool:
        """Delete key from Redis with circuit breaker"""
        self._metrics["operations"] += 1
        
        def _delete():
            return self.client.delete(key)
            
        result = self._execute_with_circuit_breaker(_delete)
        return result > 0

    # ... other methods remain similar but remove async ...

    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        try:
            start_time = time.time()
            
            # Test connection and basic operations
            self.client.ping()
            test_key = f"health_check_{int(start_time)}"
            test_value = {"timestamp": start_time, "service": "redis"}
            
            self.set(test_key, test_value, 10)
            retrieved = self.get(test_key)
            self.delete(test_key)
            
            latency = time.time() - start_time
            
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "circuit_breaker_state": self.circuit_breaker.state,
                "connection_pool": {
                    "max_connections": self.connection_pool.max_connections,
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

    def close(self):
        """Graceful shutdown"""
        try:
            self.client.close()
            self.connection_pool.disconnect()
            logger.info("Redis client connections closed gracefully")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")