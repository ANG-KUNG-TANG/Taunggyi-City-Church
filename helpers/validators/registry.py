from typing import Type, Dict, List, Optional
from pydantic import BaseModel

_registry: Dict[str, Type[BaseModel]] = {}


def register_schema(name: str, schema: Type[BaseModel]) -> None:
    
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


# Register default schemas
try:
    from apps.tcc.usecase.entities.schemas import UserCreateSchema, UserUpdateSchema
    register_schema("user_create", UserCreateSchema)
    register_schema("user_update", UserUpdateSchema)
except ImportError:
    # Schemas module might not be available during initial setup
    pass