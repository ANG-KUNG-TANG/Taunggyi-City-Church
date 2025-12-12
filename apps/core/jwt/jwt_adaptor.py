from typing import Dict, Any, Optional, Tuple, List
import jwt
import logging
from jwt_backend import JWTBackend, TokenConfig, TokenType

logger = logging.getLogger(__name__)

class JWTAuthAdapter:
    """Adapter to unify JWT interfaces"""
    
    def __init__(self, cache=None):
        self.cache = cache
        self.backend = None
        self.config = TokenConfig()
        
    async def initialize(self):
        """Initialize the JWT backend"""
        self.backend = JWTBackend.get_instance(cache=self.cache, config=self.config)
        await self.backend.initialize()
    
    async def generate_access_token(self, user_id: int, email: str, roles: list = None) -> str:
        """Generate access token - compatible with old interface"""
        if not self.backend:
            await self.initialize()
        
        result = await self.backend.create_tokens(
            user_id=str(user_id),
            email=email,
            roles=roles or []
        )
        return result['access_token']
    
    async def generate_refresh_token(self, user_id: int) -> Tuple[str, str]:
        """Generate refresh token - compatible with old interface"""
        if not self.backend:
            await self.initialize()
        
        # You'll need to get the user's email first
        # For now, return empty token_id
        return "", ""
    
    async def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify access token - compatible with old interface"""
        if not self.backend:
            await self.initialize()
        
        is_valid, payload = await self.backend.verify_token(token, TokenType.ACCESS)
        if is_valid and payload:
            return {
                'user_id': int(payload.get('sub', 0)),
                'email': payload.get('email', ''),
                'roles': payload.get('roles', []),
                'exp': payload.get('exp')
            }
        return None

# Global instance
jwt_adapter = JWTAuthAdapter()