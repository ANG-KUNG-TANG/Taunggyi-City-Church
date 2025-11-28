import asyncio
import logging
from apps.core.cache.async_cache import AsyncRedisCache
from apps.core.cache.cache_manager import CacheManager

logging.basicConfig(level=logging.INFO)

async def test_comprehensive():
    """Comprehensive cache system test"""
    print("🧪 Running comprehensive cache tests...")
    
    # Test 1: Basic Redis connection
    print("\n1. Testing Redis connection...")
    cache = AsyncRedisCache()
    health = await cache.health_check()
    assert health['status'] in ['healthy', 'degraded'], f"Health check failed: {health}"
    print("✅ Redis connection OK")
    
    # Test 2: Cache operations
    print("\n2. Testing cache operations...")
    test_data = {"user_id": 123, "name": "John Doe", "email": "john@example.com"}
    
    # Set value
    set_result = await cache.set("user:123", test_data, 300)
    assert set_result, "Set operation failed"
    print("✅ Set operation OK")
    
    # Get value
    retrieved = await cache.get("user:123")
    assert retrieved == test_data, "Get operation failed"
    print("✅ Get operation OK")
    
    # Test 3: Cache Manager
    print("\n3. Testing Cache Manager...")
    cache_manager = CacheManager(cache)
    
    # User operations
    await cache_manager.set_user("123", test_data)
    user_data = await cache_manager.get_user("123")
    assert user_data == test_data, "Cache manager user operations failed"
    print("✅ Cache Manager user operations OK")
    
    # Test 4: Error handling
    print("\n4. Testing error handling...")
    
    # Try invalid key
    invalid_data = await cache.get("non_existent_key")
    assert invalid_data is None, "Non-existent key should return None"
    print("✅ Error handling OK")
    
    # Test 5: Metrics
    print("\n5. Testing metrics...")
    stats = await cache.get_stats()
    assert 'hits' in stats and 'misses' in stats, "Metrics missing"
    print(f"📊 Final stats: {stats}")
    print("✅ Metrics collection OK")
    
    # Cleanup
    await cache.delete("user:123")
    await cache.close()
    
    print("\n🎉 All tests passed! Cache system is working correctly.")

if __name__ == "__main__":
    asyncio.run(test_comprehensive())