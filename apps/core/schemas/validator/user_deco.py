from functools import wraps
from typing import Type, Any, Dict, Optional, Union, Callable
from pydantic import BaseModel, ValidationError
from django.http import JsonResponse, HttpRequest
from rest_framework import status
from rest_framework.request import Request
import logging

from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema,
    UserUpdateInputSchema, 
    UserQueryInputSchema,
    UserSearchInputSchema,
    UserChangePasswordInputSchema,
    UserResetPasswordRequestInputSchema,
    UserResetPasswordInputSchema,
    EmailCheckInputSchema,
    PasswordVerificationInputSchema
)

logger = logging.getLogger(__name__)

def validate_with_schema(schema_class: Type[BaseModel], data_source: str = 'body'):
    """
    Generic decorator to validate input data against a Pydantic schema
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            try:
                # Extract request from context or args
                request = None
                context = kwargs.get('context', {})
                
                if 'request' in context:
                    request = context['request']
                elif args and isinstance(args[0], (HttpRequest, Request)):
                    request = args[0]
                
                if not request:
                    raise ValueError("No request found in context or arguments")
                
                # Extract data based on source
                input_data = _extract_input_data(request, data_source)
                
                # Validate with schema
                validated_data = schema_class(**input_data)
                
                # Replace the data argument with validated data
                if 'user_data' in kwargs:
                    kwargs['user_data'] = validated_data
                elif 'validated_data' in kwargs:
                    kwargs['validated_data'] = validated_data
                else:
                    # If no specific key, add as validated_data
                    kwargs['validated_data'] = validated_data
                
                return await view_func(controller_instance, *args, **kwargs)
                
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

def _extract_input_data(request: Union[HttpRequest, Request], data_source: str) -> Dict[str, Any]:
    """Extract input data from request based on data_source"""
    input_data = {}
    
    if data_source in ['body', 'all']:
        if hasattr(request, 'data') and request.data:
            input_data.update(dict(request.data))
        elif hasattr(request, 'POST') and request.POST:
            input_data.update(dict(request.POST))
    
    if data_source in ['query', 'all']:
        if hasattr(request, 'query_params') and request.query_params:
            input_data.update(dict(request.query_params))
        elif hasattr(request, 'GET') and request.GET:
            input_data.update(dict(request.GET))
    
    # Handle JSON body for REST framework
    if data_source == 'body' and not input_data and hasattr(request, 'body'):
        try:
            import json
            body_data = json.loads(request.body)
            if isinstance(body_data, dict):
                input_data.update(body_data)
        except (json.JSONDecodeError, AttributeError):
            pass
    
    return input_data

# User-specific validation decorators
def validate_user_create(view_func: Callable) -> Callable:
    """Validate user creation data using UserCreateInputSchema"""
    return validate_with_schema(UserCreateInputSchema, 'body')(view_func)

def validate_user_update(view_func: Callable) -> Callable:
    """Validate user update data using UserUpdateInputSchema"""
    return validate_with_schema(UserUpdateInputSchema, 'body')(view_func)

def validate_user_query(view_func: Callable) -> Callable:
    """Validate user query/filter data using UserQueryInputSchema"""
    return validate_with_schema(UserQueryInputSchema, 'query')(view_func)

def validate_user_search(view_func: Callable) -> Callable:
    """Validate user search data using UserSearchInputSchema"""
    return validate_with_schema(UserSearchInputSchema, 'query')(view_func)

def validate_change_password(view_func: Callable) -> Callable:
    """Validate password change data using UserChangePasswordInputSchema"""
    return validate_with_schema(UserChangePasswordInputSchema, 'body')(view_func)

def validate_reset_password_request(view_func: Callable) -> Callable:
    """Validate password reset request using UserResetPasswordRequestInputSchema"""
    return validate_with_schema(UserResetPasswordRequestInputSchema, 'body')(view_func)

def validate_reset_password(view_func: Callable) -> Callable:
    """Validate password reset data using UserResetPasswordInputSchema"""
    return validate_with_schema(UserResetPasswordInputSchema, 'body')(view_func)

def validate_email_check(view_func: Callable) -> Callable:
    """Validate email check data using EmailCheckInputSchema"""
    return validate_with_schema(EmailCheckInputSchema, 'query')(view_func)

def validate_password_verification(view_func: Callable) -> Callable:
    """Validate password verification data using PasswordVerificationInputSchema"""
    return validate_with_schema(PasswordVerificationInputSchema, 'body')(view_func)

# Business logic validation decorators
def validate_user_permissions(required_role: str = None):
    """
    Validate user permissions for specific operations
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            try:
                current_user = kwargs.get('current_user')
                context = kwargs.get('context', {})
                
                if not current_user:
                    return JsonResponse(
                        {"error": "Authentication required"},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                
                # Check role if specified
                if required_role and hasattr(current_user, 'role'):
                    if current_user.role != required_role:
                        return JsonResponse(
                            {"error": f"Required role: {required_role}"},
                            status=status.HTTP_403_FORBIDDEN
                        )
                
                # Additional business logic validations can be added here
                
                return await view_func(controller_instance, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Permission validation error: {e}")
                return JsonResponse(
                    {"error": "Permission validation failed"},
                    status=status.HTTP_403_FORBIDDEN
                )
        return _wrapped_view
    return decorator

def validate_user_ownership():
    """
    Validate that user can only modify their own data unless admin
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            try:
                current_user = kwargs.get('current_user')
                user_id = kwargs.get('user_id')
                
                if not current_user:
                    return JsonResponse(
                        {"error": "Authentication required"},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                
                # Allow admins to modify any user
                if hasattr(current_user, 'is_staff') and current_user.is_staff:
                    return await view_func(controller_instance, *args, **kwargs)
                
                # Regular users can only modify their own data
                if user_id and hasattr(current_user, 'id'):
                    if int(user_id) != current_user.id:
                        return JsonResponse(
                            {"error": "Can only modify your own data"},
                            status=status.HTTP_403_FORBIDDEN
                        )
                
                return await view_func(controller_instance, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Ownership validation error: {e}")
                return JsonResponse(
                    {"error": "Ownership validation failed"},
                    status=status.HTTP_403_FORBIDDEN
                )
        return _wrapped_view
    return decorator

# Common permission decorators (enhanced)
def require_admin(view_func: Callable) -> Callable:
    """Require admin privileges"""
    return validate_user_permissions('admin')(view_func)

def require_member(view_func: Callable) -> Callable:
    """Require member privileges (basic authenticated user)"""
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        current_user = kwargs.get('current_user')
        if not current_user or not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            return JsonResponse(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return await view_func(controller_instance, *args, **kwargs)
    return _wrapped_view

# Composite decorators for common patterns
def validate_and_authorize_user_create(view_func: Callable) -> Callable:
    """Combined validation and authorization for user creation"""
    @validate_user_create
    @require_admin  # Typically only admins can create users
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        return await view_func(controller_instance, *args, **kwargs)
    return _wrapped_view

def validate_and_authorize_user_update(view_func: Callable) -> Callable:
    """Combined validation and authorization for user updates"""
    @validate_user_update
    @validate_user_ownership()  # Users can update their own profile
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        return await view_func(controller_instance, *args, **kwargs)
    return _wrapped_view

def validate_and_authorize_user_query(view_func: Callable) -> Callable:
    """Combined validation and authorization for user queries"""
    @validate_user_query
    @require_member  # Any authenticated user can query
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        return await view_func(controller_instance, *args, **kwargs)
    return _wrapped_view