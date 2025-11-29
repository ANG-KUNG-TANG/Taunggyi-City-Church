from typing import Type, Dict, List, Optional
from pydantic import BaseModel

_registry: Dict[str, Type[BaseModel]] = {}

def register_schema(name: str, schema: Type[BaseModel]) -> None:
    """Register a schema in the global registry."""
    if not name or not isinstance(name, str):
        raise ValueError("Schema name must be a non-empty string")
    
    if not issubclass(schema, BaseModel):
        raise TypeError("Schema must be a Pydantic BaseModel")
    
    if name in _registry:
        raise ValueError(f"Schema '{name}' is already registered")
    _registry[name] = schema

def get_schema(name: str) -> Type[BaseModel]:
    """
    Get schema by name
    
    Args:
        name: Schema identifier
        
    Returns:
        The schema class
        
    Raises:
        ValueError: If schema is not found
    """
    if name not in _registry:
        raise ValueError(f"Schema '{name}' not found in registry")
    return _registry[name]

def unregister_schema(name: str) -> bool:
    """
    Unregister a schema
    
    Args:
        name: Schema identifier
        
    Returns:
        True if schema was removed, False if not found
    """
    if name in _registry:
        del _registry[name]
        return True
    return False

def get_registered_schemas() -> List[str]:
    """Get list of all registered schema names"""
    return list(_registry.keys())

def clear_registry() -> None:
    """Clear all registered schemas"""
    _registry.clear()

def schema_exists(name: str) -> bool:
    """Check if a schema is registered"""
    return name in _registry

# Register core schemas
def register_core_schemas() -> None:
    """Register all core schemas in one place"""
    try:
        from apps.core.schemas.input_schemas.u_input_schema import (
            UserCreateInputSchema, UserUpdateInputSchema, UserQueryInputSchema
        )
        from apps.core.schemas.input_schemas.auth import (
            LoginInputSchema, RegisterInputSchema, RefreshTokenInputSchema
        )
        
        # User schemas
        register_schema("user_create", UserCreateInputSchema)
        register_schema("user_update", UserUpdateInputSchema)
        register_schema("user_query", UserQueryInputSchema)
        
        # Auth schemas
        register_schema("login", LoginInputSchema)
        register_schema("register", RegisterInputSchema)
        register_schema("refresh_token", RefreshTokenInputSchema)
        
    except ImportError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not register schemas: {e}")

# Auto-register on import
register_core_schemas()