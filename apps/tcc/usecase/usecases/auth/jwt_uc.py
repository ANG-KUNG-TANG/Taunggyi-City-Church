from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import jwt
from django.conf import settings
from django.core.cache import cache
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)

class JWTAuthService:
    """JWT Authentication Service for token management"""
    
    def __init__(self):
        self.secret_key = getattr(settings, 'SECRET_KEY', 'your-secret-key-here')
        self.algorithm = "HS256"
        self.access_token_expiry = timedelta(minutes=15)  # 15 minutes
        self.refresh_token_expiry = timedelta(days=7)     # 7 days
        self.reset_token_expiry = timedelta(hours=1)      # 1 hour
    
    # ============ TOKEN GENERATION ============
    
    async def generate_access_token(self, user_id: int, email: str, roles: list = None) -> str:
        """Generate access token for user"""
        payload = {
            'user_id': user_id,
            'email': email,
            'type': 'access',
            'exp': datetime.utcnow() + self.access_token_expiry,
            'iat': datetime.utcnow(),
            'roles': roles or []
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    async def generate_refresh_token(self, user_id: int) -> Tuple[str, str]:
        """Generate refresh token and store in cache"""
        payload = {
            'user_id': user_id,
            'type': 'refresh',
            'exp': datetime.utcnow() + self.refresh_token_expiry,
            'iat': datetime.utcnow(),
            'jti': self._generate_jti()  # Unique token ID
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        token_id = payload['jti']
        
        # Store refresh token in cache
        cache_key = f"refresh_token:{user_id}:{token_id}"
        await sync_to_async(cache.set)(
            cache_key, 
            token, 
            timeout=int(self.refresh_token_expiry.total_seconds())
        )
        
        return token, token_id
    
    async def generate_reset_token(self, user_id: int, email: str) -> str:
        """Generate password reset token"""
        payload = {
            'user_id': user_id,
            'email': email,
            'type': 'reset',
            'exp': datetime.utcnow() + self.reset_token_expiry,
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store reset token in cache
        cache_key = f"reset_token:{user_id}"
        await sync_to_async(cache.set)(
            cache_key, 
            token, 
            timeout=int(self.reset_token_expiry.total_seconds())
        )
        
        return token
    
    # ============ TOKEN VERIFICATION ============
    
    async def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify access token and return payload if valid"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get('type') != 'access':
                return None
            
            # Check expiration
            exp_timestamp = payload.get('exp')
            if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.utcnow():
                return None
            
            return {
                'user_id': payload['user_id'],
                'email': payload.get('email'),
                'roles': payload.get('roles', []),
                'exp': exp_timestamp
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Access token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid access token: {str(e)}")
            return None
    
    async def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify refresh token and return payload if valid"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get('type') != 'refresh':
                return None
            
            user_id = payload.get('user_id')
            token_id = payload.get('jti')
            
            if not user_id or not token_id:
                return None
            
            # Check if token exists in cache (not blacklisted)
            cache_key = f"refresh_token:{user_id}:{token_id}"
            cached_token = await sync_to_async(cache.get)(cache_key)
            
            if not cached_token or cached_token != token:
                return None
            
            return {
                'user_id': user_id,
                'jti': token_id
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            return None
    
    async def verify_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify password reset token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get('type') != 'reset':
                return None
            
            user_id = payload.get('user_id')
            email = payload.get('email')
            
            # Check if token exists in cache
            cache_key = f"reset_token:{user_id}"
            cached_token = await sync_to_async(cache.get)(cache_key)
            
            if not cached_token or cached_token != token:
                return None
            
            return {
                'user_id': user_id,
                'email': email
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Reset token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid reset token: {str(e)}")
            return None
    
    # ============ TOKEN MANAGEMENT ============
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """Generate new access token using refresh token"""
        payload = await self.verify_refresh_token(refresh_token)
        
        if not payload:
            return None
        
        # Get user data from repository (injected via use case)
        user_id = payload['user_id']
        
        # In real implementation, you'd fetch user from repository
        # For now, return None - use case will handle user fetching
        return user_id
    
    async def blacklist_refresh_token(self, user_id: int, token_id: str):
        """Blacklist/remove refresh token"""
        cache_key = f"refresh_token:{user_id}:{token_id}"
        await sync_to_async(cache.delete)(cache_key)
    
    async def blacklist_all_user_tokens(self, user_id: int):
        """Blacklist all tokens for a user"""
        # Find and delete all refresh tokens for this user
        pattern = f"refresh_token:{user_id}:*"
        
        # Note: Django cache doesn't support pattern delete directly
        # This is a simplified version - in production, use Redis or similar
        # For now, we'll use a separate tracking mechanism
        
        # Store list of active token IDs for each user
        active_tokens_key = f"user_active_tokens:{user_id}"
        token_ids = await sync_to_async(cache.get)(active_tokens_key) or []
        
        for token_id in token_ids:
            cache_key = f"refresh_token:{user_id}:{token_id}"
            await sync_to_async(cache.delete)(cache_key)
        
        # Clear the tracking list
        await sync_to_async(cache.delete)(active_tokens_key)
    
    async def invalidate_reset_token(self, user_id: int):
        """Invalidate password reset token"""
        cache_key = f"reset_token:{user_id}"
        await sync_to_async(cache.delete)(cache_key)
    
    async def extract_token_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract payload from token without verification"""
        try:
            # Decode without verification to get payload
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except jwt.DecodeError:
            return None
    
    # ============ UTILITY METHODS ============
    
    def _generate_jti(self) -> str:
        """Generate unique JWT ID"""
        import secrets
        return secrets.token_hex(16)
    
    def get_token_expiry(self, token_type: str) -> int:
        """Get token expiry in seconds"""
        if token_type == 'access':
            return int(self.access_token_expiry.total_seconds())
        elif token_type == 'refresh':
            return int(self.refresh_token_expiry.total_seconds())
        elif token_type == 'reset':
            return int(self.reset_token_expiry.total_seconds())
        return 0
    
    async def is_token_expired(self, token: str) -> bool:
        """Check if token is expired"""
        payload = await self.extract_token_payload(token)
        
        if not payload:
            return True
        
        exp_timestamp = payload.get('exp')
        if not exp_timestamp:
            return True
        
        return datetime.fromtimestamp(exp_timestamp) < datetime.utcnow()