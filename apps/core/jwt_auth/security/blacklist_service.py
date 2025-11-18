import json
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from apps.core.jwt_auth.infrastructure.redis_client import AsyncRedisClient

logger = logging.getLogger(__name__)

class TokenBlacklistService:
    def __init__(self, redis_client: AsyncRedisClient):
        self.redis = redis_client
        self.blacklist_prefix = "blacklist:"
        self.family_prefix = "token_family:"
        self.compromised_prefix = "compromised:"

    async def blacklist_access_token(self, token: str, jti: str, user_id: str, expires_in: int) -> bool:
        """Blacklist access token with TTL matching token expiration"""
        try:
            # Store by jti for efficient lookup
            key = f"{self.blacklist_prefix}access:{jti}"
            blacklist_data = {
                'user_id': user_id,
                'blacklisted_at': datetime.utcnow().isoformat(),
                'reason': 'logout'
            }
            
            success = await self.redis.setex(
                key, 
                expires_in, 
                json.dumps(blacklist_data)
            )
            
            if success:
                logger.info(f"Access token blacklisted for user {user_id}, jti: {jti}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to blacklist access token: {e}")
            return False

    async def blacklist_refresh_token(self, token: str, jti: str, user_id: str, family_id: str) -> bool:
        """Blacklist refresh token and its family"""
        try:
            # Blacklist individual token
            token_key = f"{self.blacklist_prefix}refresh:{jti}"
            token_data = {
                'user_id': user_id,
                'family_id': family_id,
                'blacklisted_at': datetime.utcnow().isoformat()
            }
            
            # Blacklist entire token family
            family_key = f"{self.family_prefix}{user_id}:{family_id}"
            family_data = {
                'blacklisted_at': datetime.utcnow().isoformat(),
                'reason': 'rotation'
            }
            
            # Use pipeline for atomic operations
            pipeline = self.redis.pipeline()
            pipeline.setex(token_key, 86400 * 7, json.dumps(token_data))  # 7 days
            pipeline.setex(family_key, 86400 * 30, json.dumps(family_data))  # 30 days
            
            results = await pipeline.execute()
            success = all(results)
            
            if success:
                logger.info(f"Refresh token family blacklisted for user {user_id}, family: {family_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to blacklist refresh token: {e}")
            return False

    async def is_token_blacklisted(self, jti: str, token_type: str = "access") -> bool:
        """Check if token is blacklisted by jti"""
        try:
            key = f"{self.blacklist_prefix}{token_type}:{jti}"
            return await self.redis.exists(key)
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return True  # Fail secure

    async def is_token_family_blacklisted(self, user_id: str, family_id: str) -> bool:
        """Check if token family is blacklisted"""
        try:
            key = f"{self.family_prefix}{user_id}:{family_id}"
            return await self.redis.exists(key)
        except Exception as e:
            logger.error(f"Failed to check token family blacklist: {e}")
            return True  # Fail secure

    async def mark_tokens_compromised(self, user_id: str, reason: str = "suspected_compromise") -> bool:
        """Mark all tokens for a user as compromised"""
        try:
            key = f"{self.compromised_prefix}{user_id}"
            data = {
                'compromised_at': datetime.utcnow().isoformat(),
                'reason': reason
            }
            return await self.redis.setex(key, 86400, json.dumps(data))  # 24 hours
        except Exception as e:
            logger.error(f"Failed to mark tokens compromised: {e}")
            return False

    async def are_tokens_compromised(self, user_id: str) -> bool:
        """Check if user's tokens are marked as compromised"""
        try:
            key = f"{self.compromised_prefix}{user_id}"
            return await self.redis.exists(key)
        except Exception as e:
            logger.error(f"Failed to check token compromise status: {e}")
            return True  # Fail secure

    async def get_blacklist_stats(self) -> dict:
        """Get blacklist statistics for monitoring"""
        try:
            # Note: This might be expensive in production, use with caution
            access_pattern = f"{self.blacklist_prefix}access:*"
            refresh_pattern = f"{self.blacklist_prefix}refresh:*"
            family_pattern = f"{self.family_prefix}*"
            
            # In production, you might want to use Redis SCAN or maintain counters
            return {
                'feature_enabled': True,
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get blacklist stats: {e}")
            return {}