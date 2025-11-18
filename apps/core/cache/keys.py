class CacheKeys:
    """Centralized cache key management"""
    
    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"user:profile:{user_id}"
    
    @staticmethod
    def user_permissions(user_id: str) -> str:
        return f"user:permissions:{user_id}"
    
    @staticmethod
    def rate_limit(identifier: str, window: str) -> str:
        return f"rate_limit:{identifier}:{window}"
    
    @staticmethod
    def blacklisted_token(jti: str, token_type: str = "access") -> str:
        return f"blacklist:{token_type}:{jti}"
    
    @staticmethod
    def token_family(user_id: str, family_id: str) -> str:
        return f"token_family:{user_id}:{family_id}"
    
    @staticmethod
    def api_response(endpoint: str, params_hash: str) -> str:
        return f"api:response:{endpoint}:{params_hash}"
    
    @staticmethod
    def session_data(session_id: str) -> str:
        return f"session:data:{session_id}"