from functools import wraps
from typing import Type, Any, Dict, Optional, Union, Callable
from pydantic import BaseModel, ValidationError
from django.http import HttpRequest
from rest_framework.request import Request
import logging

from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema,
    UserUpdateInputSchema, 
    UserQueryInputSchema,
    UserSearchInputSchema,
    EmailCheckInputSchema,
    PasswordVerificationInputSchema
)
from apps.tcc.usecase.domain_exception.u_exceptions import (
    DomainValidationException,
    UserNotFoundException,
    UserAlreadyExistsException
)
from apps.tcc.usecase.domain_exception.auth_exceptions import AuthenticationException

logger = logging.getLogger(__name__)


# ============ CONTROLLER LAYER VALIDATION DECORATORS ============

def validate_with_schema(schema_class: Type[BaseModel], data_source: str = 'body'):
    """
    Controller layer decorator to validate input data against a Pydantic schema
    Raises DomainValidationException on failure
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            try:
                # Extract context to get request
                context = kwargs.get('context', {})
                request = context.get('request')
                
                if not request:
                    # Try to find request in args
                    for arg in args:
                        if isinstance(arg, (HttpRequest, Request)):
                            request = arg
                            break
                
                if not request:
                    raise ValueError("No request found in context or arguments")
                
                # Extract data based on source
                input_data = _extract_input_data(request, data_source)
                
                # Validate with schema
                validated_data = schema_class(**input_data)
                
                # Replace or add validated data
                if 'user_data' in kwargs:
                    kwargs['user_data'] = validated_data
                elif 'validated_data' in kwargs:
                    kwargs['validated_data'] = validated_data
                else:
                    # If controller method expects raw data, update it
                    if 'input_data' in kwargs:
                        kwargs['input_data'] = validated_data.model_dump()
                    else:
                        kwargs['validated_data'] = validated_data
                
                return await view_func(controller_instance, *args, **kwargs)
                
            except ValidationError as e:
                logger.warning(f"Validation failed for {schema_class.__name__}: {e.errors()}")
                raise DomainValidationException(
                    message="Input validation failed",
                    field_errors={error['loc'][0]: [error['msg']] for error in e.errors()}
                )
            except Exception as e:
                logger.error(f"Unexpected validation error: {e}", exc_info=True)
                raise DomainValidationException(f"Validation error: {str(e)}")
        return _wrapped_view
    return decorator


def validate_user_create(view_func: Callable) -> Callable:
    """Validate user creation data"""
    return validate_with_schema(UserCreateInputSchema, 'body')(view_func)


def validate_user_update(view_func: Callable) -> Callable:
    """Validate user update data"""
    return validate_with_schema(UserUpdateInputSchema, 'body')(view_func)


def validate_user_query(view_func: Callable) -> Callable:
    """Validate user query/filter data"""
    return validate_with_schema(UserQueryInputSchema, 'query')(view_func)


def validate_user_search(view_func: Callable) -> Callable:
    """Validate user search data"""
    return validate_with_schema(UserSearchInputSchema, 'all')(view_func)  # Search uses both query params

def validate_email_check(view_func: Callable) -> Callable:
    """Validate email check data"""
    return validate_with_schema(EmailCheckInputSchema, 'query')(view_func)


def validate_password_verification(view_func: Callable) -> Callable:
    """Validate password verification data"""
    return validate_with_schema(PasswordVerificationInputSchema, 'body')(view_func)


# ============ AUTHORIZATION DECORATORS ============

def validate_user_permissions(required_role: str = None):
    """
    Validate user permissions - raises AuthenticationException or DomainValidationException
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            current_user = kwargs.get('current_user')
            
            if not current_user:
                raise AuthenticationException("Authentication required")
            
            # Check role if specified
            if required_role and hasattr(current_user, 'role'):
                if current_user.role != required_role:
                    raise DomainValidationException(f"Required role: {required_role}")
            
            return await view_func(controller_instance, *args, **kwargs)
        return _wrapped_view
    return decorator


def validate_user_ownership():
    """
    Validate that user can only modify their own data unless admin
    Raises DomainValidationException if unauthorized
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            current_user = kwargs.get('current_user')
            user_id = kwargs.get('user_id')
            
            if not current_user:
                raise AuthenticationException("Authentication required")
            
            # Allow admins to modify any user
            if hasattr(current_user, 'is_staff') and current_user.is_staff:
                return await view_func(controller_instance, *args, **kwargs)
            
            # Regular users can only modify their own data
            if user_id and hasattr(current_user, 'id'):
                if int(user_id) != current_user.id:
                    raise DomainValidationException("You can only modify your own data")
            
            return await view_func(controller_instance, *args, **kwargs)
        return _wrapped_view
    return decorator


# ============ COMMON PERMISSION DECORATORS ============

def require_admin(view_func: Callable) -> Callable:
    """Require admin privileges - raises DomainValidationException if not admin"""
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        current_user = kwargs.get('current_user')
        
        if not current_user:
            raise AuthenticationException("Authentication required")
        
        if not hasattr(current_user, 'is_staff') or not current_user.is_staff:
            raise DomainValidationException("Admin privileges required")
        
        return await view_func(controller_instance, *args, **kwargs)
    return _wrapped_view


def require_member(view_func: Callable) -> Callable:
    """Require member authentication - raises AuthenticationException if not authenticated"""
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        current_user = kwargs.get('current_user')
        
        if not current_user:
            raise AuthenticationException("Authentication required")
        
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            raise AuthenticationException("Authentication required")
        
        return await view_func(controller_instance, *args, **kwargs)
    return _wrapped_view


# ============ COMPOSITE DECORATORS FOR COMMON PATTERNS ============

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


# ============ HELPER FUNCTIONS ============

def _extract_input_data(request: Union[HttpRequest, Request], data_source: str) -> Dict[str, Any]:
    """Extract input data from request based on data_source"""
    input_data = {}
    
    if data_source in ['body', 'all']:
        if hasattr(request, 'data') and request.data:
            # REST Framework Request
            input_data.update(dict(request.data))
        elif hasattr(request, 'POST') and request.POST:
            # Django HttpRequest
            input_data.update(dict(request.POST))
    
    if data_source in ['query', 'all']:
        if hasattr(request, 'query_params') and request.query_params:
            # REST Framework Request
            input_data.update(dict(request.query_params))
        elif hasattr(request, 'GET') and request.GET:
            # Django HttpRequest
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