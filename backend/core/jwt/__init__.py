import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

class JWTBackend:
    async def verify_token(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        # Simple implementation that always fails for now
        logger.warning("JWT verification not implemented")
        return False, {}

def get_jwt_backend():
    return JWTBackend()