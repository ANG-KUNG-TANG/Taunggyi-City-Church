# import time
# from typing import Optional
# import logging

# from apps.core.jwt_auth.infrastructure.redis_client import AsyncRedisClient

# logger = logging.getLogger(__name__)

# class RateLimiter:
#     def __init__(self, redis_client: AsyncRedisClient):
#         self.redis = redis_client
#         self.rate_limit_prefix = "rate_limit:"

#     async def check_rate_limit(self, 
#                              identifier: str, 
#                              max_requests: int, 
#                              window_seconds: int,
#                              cost: int = 1) -> dict:
#         """
#         Check if request is within rate limit using sliding window algorithm
#         """
#         try:
#             key = f"{self.rate_limit_prefix}{identifier}"
#             current_time = time.time()
#             window_start = current_time - window_seconds

#             # Remove old requests
#             pipeline = self.redis.pipeline()
#             pipeline.zremrangebyscore(key, 0, window_start)
#             pipeline.zcard(key)
#             pipeline.zrange(key, 0, -1)
#             pipeline.expire(key, window_seconds)
            
#             results = await pipeline.execute()
#             current_count = results[1]
#             requests = results[2]

#             # Check if adding this request would exceed limit
#             if current_count + cost > max_requests:
#                 oldest_request = float(requests[0]) if requests else current_time
#                 retry_after = int(window_start + window_seconds - current_time)
                
#                 return {
#                     'allowed': False,
#                     'limit': max_requests,
#                     'remaining': 0,
#                     'retry_after': retry_after,
#                     'reset_time': int(current_time + retry_after)
#                 }

#             # Add current request
#             await self.redis.zadd(key, {str(current_time): current_time})
#             await self.redis.expire(key, window_seconds)

#             return {
#                 'allowed': True,
#                 'limit': max_requests,
#                 'remaining': max_requests - (current_count + cost),
#                 'retry_after': 0,
#                 'reset_time': int(current_time + window_seconds)
#             }

#         except Exception as e:
#             logger.error(f"Rate limit check failed for {identifier}: {e}")
#             # Fail open in case of Redis issues, but log heavily
#             return {
#                 'allowed': True,
#                 'limit': max_requests,
#                 'remaining': max_requests,
#                 'retry_after': 0,
#                 'reset_time': int(time.time() + window_seconds),
#                 'error': True
#             }

#     async def get_rate_limit_status(self, identifier: str) -> dict:
#         """Get current rate limit status"""
#         try:
#             key = f"{self.rate_limit_prefix}{identifier}"
#             current_time = time.time()
            
#             count = await self.redis.zcard(key)
#             ttl = await self.redis.ttl(key)
            
#             return {
#                 'current_requests': count,
#                 'ttl': ttl,
#                 'checked_at': current_time
#             }
#         except Exception as e:
#             logger.error(f"Failed to get rate limit status: {e}")
#             return {}