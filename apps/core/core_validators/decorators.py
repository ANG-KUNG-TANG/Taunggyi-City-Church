from functools import wraps
from typing import Any, Dict, Callable, Optional

from registry import get_schema
from exceptions import ValidationError, SchemaNotFoundError


def validate(schema_name: str, data_key: str = "data"):
    """
    Decorator to validate input data against a registered schema
    
    Args:
        schema_name: Name of the schema in registry
        data_key: Key in kwargs that contains the data to validate
    
    Returns:
        Decorated function with validated data
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get schema from registry
            try:
                schema = get_schema(schema_name)
            except ValueError as e:
                raise SchemaNotFoundError(schema_name) from e
            
            # Extract data from kwargs
            raw_data = kwargs.get(data_key) or {}
            
            # Validate data against schema
            try:
                validated_data = schema(**raw_data)
            except Exception as e:
                # Convert Pydantic validation errors to our format
                error_details = _extract_pydantic_errors(e)
                raise ValidationError(
                    message="Data validation failed",
                    errors=error_details
                )
            
            # Replace original data with validated data
            kwargs[data_key] = validated_data.dict()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_optional(schema_name: str, data_key: str = "data"):
    """
    Decorator to validate input data if present, but allow None/empty data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            raw_data = kwargs.get(data_key)
            
            # Skip validation if data is None or empty
            if not raw_data:
                return func(*args, **kwargs)
            
            # Proceed with normal validation
            try:
                schema = get_schema(schema_name)
            except ValueError as e:
                raise SchemaNotFoundError(schema_name) from e
            
            try:
                validated_data = schema(**raw_data)
                kwargs[data_key] = validated_data.dict()
            except Exception as e:
                error_details = _extract_pydantic_errors(e)
                raise ValidationError(
                    message="Data validation failed",
                    errors=error_details
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _extract_pydantic_errors(validation_error: Exception) -> Dict[str, Any]:
    """
    Extract and format Pydantic validation errors
    
    Args:
        validation_error: The caught Pydantic validation exception
        
    Returns:
        Formatted error dictionary
    """
    errors = {}
    
    if hasattr(validation_error, 'errors'):
        # Pydantic V2 style errors
        for error in validation_error.errors():
            field = ".".join(str(loc) for loc in error['loc'])
            errors[field] = {
                'message': error['msg'],
                'type': error['type'],
                'input': error.get('input')
            }
    elif hasattr(validation_error, 'raw_errors'):
        # Pydantic V1 style errors or other format
        errors['_form'] = {
            'message': str(validation_error),
            'type': type(validation_error).__name__
        }
    else:
        # Fallback for other exceptions
        errors['_form'] = {
            'message': str(validation_error),
            'type': 'unknown_error'
        }
    
    return errors


# Additional validation decorators
def validate_query_params(schema_name: str):
    """Decorator to validate query parameters"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                schema = get_schema(schema_name)
            except ValueError as e:
                raise SchemaNotFoundError(schema_name) from e
            
            # Extract query params from request (assuming first arg is request)
            if args and hasattr(args[0], 'GET'):
                request = args[0]
                query_params = dict(request.GET)
                
                try:
                    validated_params = schema(**query_params)
                    # Add validated params to kwargs
                    kwargs['validated_query'] = validated_params.dict()
                except Exception as e:
                    error_details = _extract_pydantic_errors(e)
                    raise ValidationError(
                        message="Query parameter validation failed",
                        errors=error_details
                    )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator