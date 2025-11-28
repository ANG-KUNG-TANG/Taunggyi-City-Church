import asyncio
import logging
from apps.core.cache.async_cache import AsyncRedisCache

logging.basicConfig(level=logging.INFO)

async def test_basic_connection():
    """Test basic Redis connection"""
    print("🔍 Testing Redis connection...")
    
    cache = AsyncRedisCache(redis_url='redis://localhost:6379/0')
    
    try:
        # Test connection
        health = await cache.health_check()
        print(f"✅ Health status: {health['status']}")
        print(f"📊 Latency: {health.get('latency_ms', 'N/A')}ms")
        
        # Test basic operations
        await cache.set("test_key", {"hello": "world"}, 60)
        value = await cache.get("test_key")
        print(f"✅ Set/Get test: {value}")
        
        # Test delete
        await cache.delete("test_key")
        print("✅ Delete test: Success")
        
        # Get stats
        stats = await cache.get_stats()
        print(f"📈 Stats: {stats}")
        
        await cache.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_basic_connection())