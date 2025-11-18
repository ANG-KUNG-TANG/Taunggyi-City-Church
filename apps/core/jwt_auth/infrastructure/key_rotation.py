# import jwt
# from datetime import datetime, timedelta
# from typing import Dict, Any, Optional
# import logging

# from apps.core.jwt_auth.infrastructure.redis_client import AsyncRedisClient

# logger = logging.getLogger(__name__)

# class KeyRotationManager:
#     def __init__(self, redis_client: AsyncRedisClient):
#         self.redis = redis_client
#         self.key_version_prefix = "jwt_key_version:"
#         self.key_rotation_interval = timedelta(days=30)

#     async def rotate_keys_if_needed(self) -> bool:
#         """Rotate JWT keys if rotation interval has passed"""
#         try:
#             current_version = await self._get_current_key_version()
#             last_rotation = await self._get_last_rotation_date(current_version)
            
#             if last_rotation and datetime.utcnow() - last_rotation < self.key_rotation_interval:
#                 return False
            
#             # Perform key rotation
#             new_version = await self._perform_key_rotation(current_version)
#             logger.info(f"JWT key rotated to version {new_version}")
#             return True
            
#         except Exception as e:
#             logger.error(f"Key rotation failed: {e}")
#             return False

#     async def _get_current_key_version(self) -> str:
#         """Get current key version"""
#         version = await self.redis.get(f"{self.key_version_prefix}current")
#         return version.decode('utf-8') if version else "v1"

#     async def _get_last_rotation_date(self, version: str) -> Optional[datetime]:
#         """Get last rotation date for version"""
#         date_str = await self.redis.get(f"{self.key_version_prefix}{version}:rotation_date")
#         if date_str:
#             return datetime.fromisoformat(date_str.decode('utf-8'))
#         return None

#     async def _perform_key_rotation(self, current_version: str) -> str:
#         """Perform actual key rotation"""
#         new_version = f"v{int(current_version[1:]) + 1}"
        
#         # In production, you would:
#         # 1. Generate new RSA key pair
#         # 2. Store new private key securely
#         # 3. Update public key distribution
#         # 4. Mark old version for phase-out
        
#         rotation_data = {
#             'previous_version': current_version,
#             'new_version': new_version,
#             'rotated_at': datetime.utcnow().isoformat()
#         }
        
#         # Store rotation metadata
#         await self.redis.setex(
#             f"{self.key_version_prefix}rotation_log:{new_version}",
#             86400 * 90,  # 90 days
#             rotation_data
#         )
        
#         # Update current version
#         await self.redis.set(f"{self.key_version_prefix}current", new_version)
        
#         return new_version

#     async def validate_token_version(self, token_payload: Dict[str, Any]) -> bool:
#         """Validate that token uses acceptable key version"""
#         try:
#             token_version = token_payload.get('key_version', 'v1')
#             current_version = await self._get_current_key_version()
            
#             # Allow current and previous version during grace period
#             allowed_versions = [current_version]
#             if token_version == f"v{int(current_version[1:]) - 1}":
#                 # Check if previous version is still within grace period
#                 rotation_date = await self._get_last_rotation_date(current_version)
#                 if rotation_date and datetime.utcnow() - rotation_date < timedelta(days=7):
#                     allowed_versions.append(token_version)
            
#             return token_version in allowed_versions
            
#         except Exception as e:
#             logger.error(f"Token version validation failed: {e}")
#             return False