from typing import Any, Dict, List
import hashlib
import json


class CacheKeyGenerator:
    """Helper class for generating consistent cache keys"""
    
    @staticmethod
    def generate_key(prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix, args and kwargs"""
        key_parts = [prefix]
        
        # Add args to key
        for arg in args:
            key_parts.append(str(arg))
        
        # Add kwargs to key in sorted order for consistency
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        full_key = ":".join(key_parts)
        
        # If key is too long, use hash
        if len(full_key) > 200:
            hash_obj = hashlib.md5(full_key.encode())
            return f"{prefix}:{hash_obj.hexdigest()}"
        
        return full_key
    
    @staticmethod
    def model_key(model_name: str, instance_id: Any, field: str = None) -> str:
        """Generate key for model instances"""
        key = f"model:{model_name}:{instance_id}"
        if field:
            key += f":{field}"
        return key
    
    @staticmethod
    def user_key(user_id: Any, resource: str = None) -> str:
        """Generate key for user-related data"""
        key = f"user:{user_id}"
        if resource:
            key += f":{resource}"
        return key
    
    @staticmethod
    def api_key(endpoint: str, params: Dict[str, Any] = None) -> str:
        """Generate key for API responses"""
        key = f"api:{endpoint}"
        if params:
            param_str = json.dumps(params, sort_keys=True)
            hash_obj = hashlib.md5(param_str.encode())
            key += f":{hash_obj.hexdigest()}"
        return key
    
    @staticmethod
    def function_key(func_name: str, args: tuple, kwargs: Dict[str, Any]) -> str:
        """Generate key for function results"""
        args_str = json.dumps(args, sort_keys=True, default=str)
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        combined = f"{args_str}:{kwargs_str}"
        hash_obj = hashlib.md5(combined.encode())
        return f"func:{func_name}:{hash_obj.hexdigest()}"


# Global instance
key_generator = CacheKeyGenerator()