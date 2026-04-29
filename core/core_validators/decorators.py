from functools import wraps
from typing import Type, Any, Dict, Optional, Union
from pydantic import BaseModel, ValidationError
from django.http import JsonResponse, HttpRequest
from rest_framework import status
from rest_framework.request import Request
import logging

logger = logging.getLogger(__name__)

def validate_input(
    schema_class: Type[BaseModel],
    data_source: str = 'body'  # 'body', 'query', or 'all'
):
    """
    Decorator to validate input data against a Pydantic schema
    
    Args:
        schema_class: Pydantic schema class to validate against
        data_source: Where to extract data from - 'body', 'query', or 'all'
    """
    def decorator(view_func):
        @wraps(view_func)
        async def _wrapped_view(request, *args, **kwargs):
            try:
                input_data = _extract_input_data(request, data_source)
                
                # Validate data against schema
                validated_data = schema_class(**input_data)
                
                # Pass validated data to view
                kwargs['validated_data'] = validated_data
                
                return await view_func(request, *args, **kwargs)
                
            except ValidationError as e:
                logger.warning(f"Validation failed for {schema_class.__name__}: {e.errors()}")
                return JsonResponse(
                    {
                        "error": "Validation failed",
                        "details": e.errors(),
                        "message": "Invalid input data"
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            except Exception as e:
                logger.error(f"Unexpected validation error: {e}", exc_info=True)
                return JsonResponse(
                    {
                        "error": "Validation error",
                        "details": str(e),
                        "message": "Input validation failed"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        return _wrapped_view
    return decorator

def _extract_input_data(
    request: Union[HttpRequest, Request], 
    data_source: str
) -> Dict[str, Any]:
    """Extract input data from request based on data_source"""
    input_data = {}
    
    if data_source in ['body', 'all'] and hasattr(request, 'data'):
        input_data.update(request.data)
    
    if data_source in ['query', 'all'] and hasattr(request, 'query_params'):
        input_data.update(dict(request.query_params))
    elif data_source in ['query', 'all'] and hasattr(request, 'GET'):
        input_data.update(dict(request.GET))
    
    return input_data

# Schema-specific validation decorators
def create_schema_validator(schema_class: Type[BaseModel], data_source: str = 'body'):
    """Factory function to create schema-specific validators"""
    def decorator(view_func):
        return validate_input(schema_class, data_source)(view_func)
    return decorator

# Import schemas only when needed to avoid circular imports
def _get_schema_class(schema_name: str) -> Type[BaseModel]:
    """Get schema class by name from registry"""
    from .registry import get_schema
    return get_schema(schema_name)

# Dynamic validators using registry
def validate_with_schema(schema_name: str, data_source: str = 'body'):
    """Validate using schema from registry by name"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            schema_class = _get_schema_class(schema_name)
            return validate_input(schema_class, data_source)(view_func)(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Permission decorators with basic implementation
def require_permission(permission: str):
    """Require specific permission"""
    def decorator(view_func):
        @wraps(view_func)
        async def _wrapped_view(request, *args, **kwargs):
            # TODO: Implement actual permission checking
            # For now, this is a placeholder
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return JsonResponse(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            return await view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Common permission decorators
require_admin = require_permission('admin')
require_member = require_permission('member')
require_authenticated = require_permission('authenticated')