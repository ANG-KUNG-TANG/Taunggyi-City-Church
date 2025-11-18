"""
Redis Client Factory with Singleton Pattern
Reliability Level: HIGH
"""
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from .redis_client import RedisClient

logger = logging.getLogger(__name__)

class RedisFactory:
    """
    Production Redis Client Factory
    Reliability Level: HIGH
    Responsibilities: Connection management, configuration, singleton pattern
    """
    
    _instances: Dict[str, RedisClient] = {}
    _default_instance: Optional[RedisClient] = None
    
    @classmethod
    def get_client(
        cls,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: str = None,
        max_connections: int = 20,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
        instance_name: str = "default"
    ) -> RedisClient:
        """
        Get Redis client instance (singleton per configuration)
        Reliability Level: HIGH
        """
        config_key = f"{host}:{port}:{db}:{instance_name}"
        
        if config_key not in cls._instances:
            cls._instances[config_key] = RedisClient(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                retry_on_timeout=retry_on_timeout,
                health_check_interval=health_check_interval
            )
            
            if instance_name == "default":
                cls._default_instance = cls._instances[config_key]
                
            logger.info(f"Created new Redis client instance: {config_key}")
        
        return cls._instances[config_key]
    
    @classmethod
    def get_default_client(cls) -> Optional[RedisClient]:
        """Get default Redis client instance"""
        return cls._default_instance
    
    @classmethod
    async def close_all(cls):
        """Close all Redis client connections"""
        for name, client in cls._instances.items():
            try:
                await client.close()
                logger.info(f"Closed Redis client: {name}")
            except Exception as e:
                logger.error(f"Error closing Redis client {name}: {e}")
        
        cls._instances.clear()
        cls._default_instance = None
        logger.info("All Redis client connections closed")
    
    @classmethod
    async def health_check_all(cls) -> Dict[str, Any]:
        """Health check for all Redis instances"""
        results = {}
        
        for name, client in cls._instances.items():
            try:
                health = await client.health_check()
                results[name] = health
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return {
            "total_instances": len(results),
            "healthy_instances": sum(1 for r in results.values() if r.get("status") == "healthy"),
            "instances": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @classmethod
    def get_instance_count(cls) -> int:
        """Get number of active Redis instances"""
        return len(cls._instances)