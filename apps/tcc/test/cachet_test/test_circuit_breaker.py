import asyncio
import logging
from apps.core.cache.async_cache import AsyncRedisCache

logging.basicConfig(level=logging.INFO)

async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("🔌 Testing circuit breaker...")
    
    # Use invalid Redis URL to trigger circuit breaker
    cache = AsyncRedisCache(redis_url='redis://invalid-host:6379/0')
    
    try:
        # These should trigger circuit breaker
        for i in range(6):  # More than failure threshold
            try:
                await cache.set(f"key_{i}", "value", 60)
            except Exception as e:
                print(f"Attempt {i+1}: {e}")
        
        # Check circuit breaker state
        stats = await cache.get_stats()
        print(f"🔧 Circuit breaker state: {stats['circuit_breaker_state']}")
        print(f"📊 Failures: {stats['circuit_breaker_trips']}")
        
    except Exception as e:
        print(f"❌ Circuit breaker test failed: {e}")
    
    finally:
        await cache.close()

if __name__ == "__main__":
    asyncio.run(test_circuit_breaker())