"""
Three-Layer Authorization Decorators for Django/DRF

Design Philosophy:
1. Security by Default - endpoints require authentication unless explicitly marked public
2. Clear Separation - authentication vs authorization concerns
3. Minimal Role Checks - roles used sparingly, ownership used frequently
4. Admin Bypass - admins can bypass ownership for operational workflows
"""

from functools import wraps
from typing import Type, Any, Dict, Optional, Union, Callable
from pydantic import BaseModel, ValidationError
from django.http import HttpRequest
from rest_framework.request import Request
import logging

from apps.core.core_exceptions.domain import ValidationException
from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema,
    UserUpdateInputSchema,
    UserQueryInputSchema,
    UserSearchInputSchema,
    EmailCheckInputSchema,
    PasswordVerificationInputSchema
)
from apps.tcc.usecase.domain_exception.u_exceptions import DomainValidationException
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    AuthenticationException,
    AuthorizationException
)

logger = logging.getLogger(__name__)


# ============ CORE AUTHORIZATION DECORATORS ============

def public_endpoint(view_func: Callable) -> Callable:
    """
    LAYER 0: Explicitly marks endpoint as public (no authentication).
    
    Rationale:
    - Makes security posture EXPLICIT
    - Used for registration, login, email checks, health endpoints
    - Prevents accidental exposure of private endpoints
    """
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        # No authentication check - just pass through
        return await view_func(controller_instance, *args, **kwargs)
    return _wrapped_view


def require_authenticated(view_func: Callable) -> Callable:
    """
    LAYER 1: Default authentication - any logged-in user can access.
    
    Usage: 80% of endpoints should use this
    Design: Simple check, no role or ownership constraints
    """
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        current_user = kwargs.get('current_user')
        
        # Check if user object exists and is authenticated
        if not current_user:
            raise AuthenticationException("Authentication required")
        
        # Support both Django User and custom user objects
        if hasattr(current_user, 'is_authenticated') and not current_user.is_authenticated:
            raise AuthenticationException("Authentication required")
        
        return await view_func(controller_instance, *args, **kwargs)
    return _wrapped_view


def require_ownership(resource_param: str = 'user_id', user_attr: str = 'id'):
    """
    LAYER 2: Ownership validation with admin bypass.
    
    Rationale:
    - resource_param: Which parameter holds the resource ID
    - user_attr: Which user attribute to compare against
    - Admin bypass: Critical for support workflows
    
    Usage: User profile updates, personal data access
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            current_user = kwargs.get('current_user')
            resource_id = kwargs.get(resource_param)
            
            # Authentication check first
            if not current_user:
                raise AuthenticationException("Authentication required")
            
            # ADMIN BYPASS - Critical design decision
            if hasattr(current_user, 'is_staff') and current_user.is_staff:
                logger.debug(f"Admin bypass for resource {resource_param}={resource_id}")
                return await view_func(controller_instance, *args, **kwargs)
            
            # Ownership check
            if resource_id is not None:
                user_identifier = getattr(current_user, user_attr, None)
                if user_identifier is None:
                    raise AuthorizationException("User identifier not found")
                
                # Compare resource ID with user's identifier
                if str(resource_id) != str(user_identifier):
                    logger.warning(
                        f"Ownership violation: user {user_identifier} tried to access {resource_param}={resource_id}"
                    )
                    raise AuthorizationException(
                        f"You don't have permission to access this resource"
                    )
            
            return await view_func(controller_instance, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_role(*allowed_roles: str):
    """
    LAYER 3: Explicit role-based authorization.
    
    Design Principles:
    1. Use SPARINGLY - only for sensitive/global operations
    2. Explicit roles - avoid magic strings, document clearly
    3. Minimal role proliferation - avoid role explosion
    
    Usage: System-wide operations (delete users, view all data)
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            current_user = kwargs.get('current_user')
            
            if not current_user:
                raise AuthenticationException("Authentication required")
            
            # Get user role (supports multiple attribute names)
            user_role = (
                getattr(current_user, 'role', None) or
                getattr(current_user, 'user_type', None) or
                getattr(current_user, 'role_type', None)
            )
            
            # Check if user has any of the allowed roles
            if not user_role or user_role not in allowed_roles:
                allowed_str = ", ".join(allowed_roles)
                logger.warning(
                    f"Role violation: user has role '{user_role}', requires: {allowed_str}"
                )
                raise AuthorizationException(
                    f"Required roles: {allowed_str}"
                )
            
            return await view_func(controller_instance, *args, **kwargs)
        return _wrapped_view
    return decorator


# ============ COMMON SHORTCUTS ============

def require_admin(view_func: Callable) -> Callable:
    """Shortcut for admin-only endpoints"""
    return require_role('admin')(view_func)


def require_superuser(view_func: Callable) -> Callable:
    """Shortcut for superuser-only endpoints"""
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        current_user = kwargs.get('current_user')
        
        if not current_user:
            raise AuthenticationException("Authentication required")
        
        if not hasattr(current_user, 'is_superuser') or not current_user.is_superuser:
            raise AuthorizationException("Superuser privileges required")
        
        return await view_func(controller_instance, *args, **kwargs)
    return _wrapped_view


# ============ COMPOSITE DECORATORS (REAL-WORLD PATTERNS) ============

def authenticated_with_ownership(
    resource_param: str = 'user_id',
    user_attr: str = 'id'
):
    """
    Composite: Authentication + Ownership.
    
    Rationale: Most common pattern for user resources
    Reduces decorator stacking in controllers
    """
    def decorator(view_func: Callable) -> Callable:
        @require_authenticated
        @require_ownership(resource_param, user_attr)
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            return await view_func(controller_instance, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_or_owner(resource_param: str = 'user_id', user_attr: str = 'id'):
    """
    Composite: Admin can access anything, users can only access their own.
    
    Design Decision: Admin bypass is explicit in logic
    Usage: Admin dashboards, support tools
    """
    def decorator(view_func: Callable) -> Callable:
        @require_authenticated
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            current_user = kwargs.get('current_user')
            resource_id = kwargs.get(resource_param)
            
            # Admin bypass
            is_admin = (
                hasattr(current_user, 'is_staff') and current_user.is_staff or
                hasattr(current_user, 'is_superuser') and current_user.is_superuser or
                (hasattr(current_user, 'role') and current_user.role == 'admin')
            )
            
            if is_admin:
                logger.debug(f"Admin access granted for {resource_param}={resource_id}")
                return await view_func(controller_instance, *args, **kwargs)
            
            # Ownership check for non-admins
            if resource_id is not None:
                user_identifier = getattr(current_user, user_attr, None)
                if user_identifier and str(resource_id) != str(user_identifier):
                    raise AuthorizationException(
                        "You don't have permission to access this resource"
                    )
            
            return await view_func(controller_instance, *args, **kwargs)
        return _wrapped_view
    return decorator


def public_or_authenticated(view_func: Callable) -> Callable:
    """
    Composite: Public access OR authenticated access.
    
    Usage: Mixed endpoints (e.g., view public profile but edit requires auth)
    """
    @wraps(view_func)
    async def _wrapped_view(controller_instance, *args, **kwargs):
        current_user = kwargs.get('current_user')
        
        # If user is authenticated, allow access
        if current_user and hasattr(current_user, 'is_authenticated'):
            if current_user.is_authenticated:
                return await view_func(controller_instance, *args, **kwargs)
        
        # For public access, we need to handle differently
        # This is context-dependent and might need custom logic
        raise AuthenticationException("Authentication required for this operation")
    return _wrapped_view


# ============ VALIDATION DECORATORS (KEEP EXISTING) ============

def validate_with_schema(schema_class: Type[BaseModel], data_source: str = 'body'):
    """Controller-layer validation with Pydantic schemas"""
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            try:
                # Extract request from context or args
                request = None
                context = kwargs.get('context', {})
                
                if 'context' in kwargs and isinstance(kwargs['context'], dict):
                    request = kwargs['context'].get('request')
                
                if not request:
                    for arg in args:
                        if isinstance(arg, (HttpRequest, Request)):
                            request = arg
                            break
                
                if not request:
                    raise ValueError("No request found in context or arguments")
                
                # Extract and validate data
                input_data = _extract_input_data(request, data_source)
                validated_data = schema_class(**input_data)
                
                # Inject validated data into kwargs
                if 'user_data' in kwargs:
                    kwargs['user_data'] = validated_data
                elif 'validated_data' in kwargs:
                    kwargs['validated_data'] = validated_data
                else:
                    # Default to validated_data
                    kwargs['validated_data'] = validated_data
                
                return await view_func(controller_instance, *args, **kwargs)
                
            except ValidationError as e:
                logger.warning(f"Validation failed for {schema_class.__name__}: {e.errors()}")
                raise DomainValidationException(
                    message="Input validation failed",
                    field_errors=_format_validation_errors(e.errors())
                )
            except Exception as e:
                from apps.tcc.usecase.domain_exception.u_exceptions import UserAlreadyExistsException
                from apps.core.core_exceptions.domain import BusinessRuleException
                
                if isinstance(e, (UserAlreadyExistsException, BusinessRuleException)):
                    status_code = getattr(e, 'status_code', 409)
                    raise ValidationException(
                        message=str(e),
                        details=getattr(e, 'details', {})
                    )
                else:
                    raise ValidationException(
                        message=f"Validation error: {str(e)}",
                        status_code=422
                    )
        return _wrapped_view
    return decorator


# Specific validation decorators (keep existing)
def validate_user_create(view_func: Callable) -> Callable:
    return validate_with_schema(UserCreateInputSchema, 'body')(view_func)


def validate_user_update(view_func: Callable) -> Callable:
    return validate_with_schema(UserUpdateInputSchema, 'body')(view_func)


def validate_user_query(view_func: Callable) -> Callable:
    return validate_with_schema(UserQueryInputSchema, 'query')(view_func)


def validate_user_search(view_func: Callable) -> Callable:
    return validate_with_schema(UserSearchInputSchema, 'all')(view_func)


def validate_email_check(view_func: Callable) -> Callable:
    return validate_with_schema(EmailCheckInputSchema, 'query')(view_func)


def validate_password_verification(view_func: Callable) -> Callable:
    return validate_with_schema(PasswordVerificationInputSchema, 'body')(view_func)


# ============ COMPOSITE VALIDATION + AUTHORIZATION ============

def validate_and_authorize_create(schema_class: Type[BaseModel], require_admin: bool = True):
    """
    Composite: Validation + Authorization for creation endpoints.
    
    Rationale: Creation often requires admin privileges
    Can be configured for public creation (registration)
    """
    def decorator(view_func: Callable) -> Callable:
        if require_admin:
            @validate_with_schema(schema_class, 'body')
            @require_admin
            @wraps(view_func)
            async def _wrapped_view(controller_instance, *args, **kwargs):
                return await view_func(controller_instance, *args, **kwargs)
        else:
            @validate_with_schema(schema_class, 'body')
            @public_endpoint
            @wraps(view_func)
            async def _wrapped_view(controller_instance, *args, **kwargs):
                return await view_func(controller_instance, *args, **kwargs)
        return _wrapped_view
    return decorator


def validate_and_authorize_update(schema_class: Type[BaseModel]):
    """
    Composite: Validation + Ownership for update endpoints.
    
    Rationale: Users can update their own data
    Combines validation with ownership check
    """
    def decorator(view_func: Callable) -> Callable:
        @validate_with_schema(schema_class, 'body')
        @authenticated_with_ownership('user_id', 'id')
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            return await view_func(controller_instance, *args, **kwargs)
        return _wrapped_view
    return decorator


def validate_and_authorize_query(schema_class: Type[BaseModel]):
    """
    Composite: Validation + Authentication for query endpoints.
    
    Rationale: Any authenticated user can query
    """
    def decorator(view_func: Callable) -> Callable:
        @validate_with_schema(schema_class, 'query')
        @require_authenticated
        @wraps(view_func)
        async def _wrapped_view(controller_instance, *args, **kwargs):
            return await view_func(controller_instance, *args, **kwargs)
        return _wrapped_view
    return decorator


# ============ HELPER FUNCTIONS ============

def _extract_input_data(request: Union[HttpRequest, Request], data_source: str) -> Dict[str, Any]:
    """Extract input data from request based on source"""
    input_data = {}
    
    # Body data
    if data_source in ['body', 'all']:
        if hasattr(request, 'data') and request.data:
            # REST Framework Request
            input_data.update(dict(request.data))
        elif hasattr(request, 'POST') and request.POST:
            # Django HttpRequest
            input_data.update(dict(request.POST))
        
        # Handle JSON body
        if not input_data and hasattr(request, 'body'):
            try:
                import json
                body_data = json.loads(request.body)
                if isinstance(body_data, dict):
                    input_data.update(body_data)
            except (json.JSONDecodeError, AttributeError):
                pass
    
    # Query parameters
    if data_source in ['query', 'all']:
        if hasattr(request, 'query_params') and request.query_params:
            input_data.update(dict(request.query_params))
        elif hasattr(request, 'GET') and request.GET:
            input_data.update(dict(request.GET))
    
    return input_data


def _format_validation_errors(errors: list) -> Dict[str, list]:
    """Format Pydantic validation errors for domain exceptions"""
    field_errors = {}
    for error in errors:
        # Get field name (could be nested)
        field = '.'.join(str(loc) for loc in error['loc']) if error['loc'] else 'non_field'
        
        # Skip '__root__' for root-level errors
        if field == '__root__':
            field = 'non_field'
        
        if field not in field_errors:
            field_errors[field] = []
        
        field_errors[field].append(error['msg'])
    
    return field_errors


# ============ DEPRECATION/COMPATIBILITY ============

def require_member(view_func: Callable) -> Callable:
    """Legacy support - maps to require_authenticated"""
    import warnings
    warnings.warn(
        "require_member is deprecated, use require_authenticated instead",
        DeprecationWarning
    )
    return require_authenticated(view_func)


def validate_user_ownership():
    """Legacy support - maps to require_ownership"""
    import warnings
    warnings.warn(
        "validate_user_ownership is deprecated, use require_ownership instead",
        DeprecationWarning
    )
    return require_ownership('user_id', 'id')