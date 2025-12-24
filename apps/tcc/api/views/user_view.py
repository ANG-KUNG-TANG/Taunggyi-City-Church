"""
DRF Views with JWT Authentication and Domain Exception Handling

Design Principles:
1. DRF handles JWT authentication (request.user population)
2. Views extract current_user and inject into controllers
3. Centralized exception handler converts domain exceptions to HTTP
4. Views handle HTTP concerns ONLY (responses, status codes)
"""

import json
import logging
from typing import Dict, Any, List, Optional
from functools import wraps
from django.http import HttpRequest, JsonResponse
from rest_framework.request import Request
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.core.cache import cache as django_cache

from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema,
    UserUpdateInputSchema,
    UserQueryInputSchema,
    UserSearchInputSchema,
    EmailCheckInputSchema,
)
from apps.tcc.usecase.entities.users_entity import UserEntity
from apps.core.cache.async_cache import AsyncCache
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.services.users.user_controller import get_user_controller
from apps.tcc.usecase.domain_exception.u_exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
    PasswordValidationException,
    AccountLockedException
)
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    AuthenticationException,
    AuthorizationException
)
from apps.core.core_exceptions.domain import (
    DomainValidationException,
    DomainException
)

logger = logging.getLogger(__name__)


# ============ CORE UTILITIES ============

def get_current_user_from_request(request: Request) -> Optional[Any]:
    """
    Extract current user from DRF-authenticated request
    
    Design: Creates a simple object with expected attributes
    Note: DRF JWT middleware already populated request.user
    """
    if not hasattr(request, 'user'):
        return None
    
    user = request.user
    
    # Check if user is authenticated (DRF handles this)
    if not user.is_authenticated:
        return None
    
    # Create a simple object with expected attributes
    class CurrentUser:
        def __init__(self, user):
            self.id = user.id
            self.username = user.username
            self.email = getattr(user, 'email', '')
            self.is_staff = user.is_staff
            self.is_superuser = user.is_superuser
            self.is_active = user.is_active
            self.is_authenticated = user.is_authenticated
            
            # Try to get role from various possible attributes
            self.role = getattr(user, 'role', None) or \
                       getattr(user, 'user_type', None) or \
                       getattr(user, 'role_type', None) or \
                       'user'
    
    return CurrentUser(user)


def entity_to_dict(entity: UserEntity) -> Dict[str, Any]:
    """
    Convert UserEntity to safe dictionary for API response
    
    Design: Removes sensitive information, formats dates
    """
    if not entity:
        return {}
    
    try:
        # Try Pydantic v2 model_dump first
        entity_dict = entity.model_dump()
    except AttributeError:
        # Fallback for Pydantic v1
        if hasattr(entity, 'dict'):
            entity_dict = entity.dict()
        elif hasattr(entity, '__dict__'):
            entity_dict = entity.__dict__.copy()
        else:
            return {}
    
    # Remove sensitive fields
    SENSITIVE_FIELDS = [
        'password', 'password_hash', 'salt', 'tokens',
        'refresh_token', 'access_token', 'secret_key'
    ]
    for field in SENSITIVE_FIELDS:
        entity_dict.pop(field, None)
    
    # Convert dates to ISO format
    DATE_FIELDS = [
        'created_at', 'updated_at', 'last_login',
        'date_of_birth', 'membership_date'
    ]
    for field in DATE_FIELDS:
        if field in entity_dict and entity_dict[field]:
            value = entity_dict[field]
            if hasattr(value, 'isoformat'):
                entity_dict[field] = value.isoformat()
            elif hasattr(value, 'strftime'):
                entity_dict[field] = value.strftime('%Y-%m-%dT%H:%M:%S')
    
    return entity_dict


def entities_to_list(entities: List[UserEntity]) -> List[Dict[str, Any]]:
    """Convert list of UserEntity to list of dictionaries"""
    return [entity_to_dict(entity) for entity in entities] if entities else []


def create_paginated_response(
    items: List[Dict[str, Any]],
    total_count: int,
    page: int,
    per_page: int,
    **additional_data
) -> Dict[str, Any]:
    """Standardized paginated response format"""
    total_pages = max(1, (total_count + per_page - 1) // per_page) if per_page > 0 else 1
    
    return {
        'items': items,
        'pagination': {
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        },
        **additional_data
    }


# ============ EXCEPTION HANDLER ============

class UserAPIExceptionHandler:
    """
    Centralized exception handler for ALL user API endpoints
    
    Design: Converts domain exceptions to proper HTTP responses
    Keeps HTTP concerns separate from business logic
    """
    
    # Domain Exception → HTTP Status Code Mapping
    EXCEPTION_MAP = {
        # 400 - Bad Request
        DomainValidationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        PasswordValidationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        
        # 401 - Unauthorized
        AuthenticationException: status.HTTP_401_UNAUTHORIZED,
        
        # 403 - Forbidden
        AuthorizationException: status.HTTP_403_FORBIDDEN,
        
        # 404 - Not Found
        UserNotFoundException: status.HTTP_404_NOT_FOUND,
        
        # 409 - Conflict
        UserAlreadyExistsException: status.HTTP_409_CONFLICT,
        
        # 423 - Locked
        AccountLockedException: status.HTTP_423_LOCKED,
    }
    
    @classmethod
    def handle_exception(cls, exc: Exception) -> JsonResponse:
        """Convert any domain exception to proper API response"""
        
        # Log based on exception type
        if isinstance(exc, (AuthenticationException, AuthorizationException)):
            logger.warning(f"Auth exception: {type(exc).__name__}: {exc}")
        elif isinstance(exc, DomainValidationException):
            logger.info(f"Validation exception: {type(exc).__name__}: {exc}")
        elif isinstance(exc, (UserNotFoundException, UserAlreadyExistsException)):
            logger.info(f"Business exception: {type(exc).__name__}: {exc}")
        else:
            logger.error(f"Unexpected exception: {type(exc).__name__}: {exc}", exc_info=True)
        
        # Get HTTP status code
        status_code = cls.EXCEPTION_MAP.get(
            type(exc),
            getattr(exc, 'status_code', status.HTTP_400_BAD_REQUEST)
        )
        
        # Build error response
        error_data = {
            "success": False,
            "message": cls._get_user_message(exc),
            "code": type(exc).__name__.upper(),
            "status_code": status_code
        }
        
        # Add field errors for validation exceptions
        if isinstance(exc, DomainValidationException):
            if hasattr(exc, 'field_errors') and exc.field_errors:
                error_data["errors"] = exc.field_errors
        
        # Add specific details if available
        if hasattr(exc, 'details') and exc.details:
            error_data["details"] = exc.details
        
        return JsonResponse(error_data, status=status_code)
    
    @classmethod
    def _get_user_message(cls, exc: Exception) -> str:
        """Get user-friendly message from exception"""
        if hasattr(exc, 'user_message') and exc.user_message:
            return exc.user_message
        return str(exc)
    
    @classmethod
    def as_decorator(cls, func):
        """Decorator to wrap view functions with exception handling"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return cls.handle_exception(e)
        return wrapper


# ============ VIEW DECORATORS ============

def inject_current_user(func):
    """
    Decorator to inject current_user into view functions
    
    Design: Extracts user from request and adds to kwargs
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        current_user = get_current_user_from_request(request)
        return await func(request, *args, current_user=current_user, **kwargs)
    return wrapper


def validate_request_schema(schema_class):
    """
    Decorator to validate request data against Pydantic schema
    
    Design: View-layer validation before controller
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                # Validate based on request method
                if request.method in ['POST', 'PUT', 'PATCH']:
                    validated_data = schema_class(**request.data)
                else:  # GET, DELETE
                    validated_data = schema_class(**request.query_params.dict())
                
                # Add validated data to kwargs
                return await func(request, *args, validated_data=validated_data, **kwargs)
            except Exception as e:
                return UserAPIExceptionHandler.handle_exception(e)
        return wrapper
    return decorator


# ============ API ENDPOINTS ============

@api_view(['POST'])
@permission_classes([AllowAny])
@UserAPIExceptionHandler.as_decorator
async def register_user_view(request: Request) -> JsonResponse:
    controller = await get_user_controller()
    
    # Validate input
    user_data = UserCreateInputSchema(**request.data)
    
    # Call controller (no current_user for public registration)
    user_entity = await controller.register_user(
        user_data=user_data,
        context={'request': request, 'ip_address': request.META.get('REMOTE_ADDR')}
    )
    
    # Build success response
    return JsonResponse(
        APIResponse.create_success(
            data=entity_to_dict(user_entity),
            message="User registered successfully",
            status_code=status.HTTP_201_CREATED
        ).to_dict(),
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def create_admin_user_view(
    request: Request,
    current_user: Any
) -> JsonResponse:
    """
    ADMIN-ONLY: Create admin user
    
    Endpoint: POST /api/users/admin/create/
    Security: Admin only
    """
    controller = await get_user_controller()
    
    user_data = UserCreateInputSchema(**request.data)
    
    user_entity = await controller.create_admin_user(
        user_data=user_data,
        current_user=current_user,
        context={'request': request}
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=entity_to_dict(user_entity),
            message="Admin user created successfully",
            status_code=status.HTTP_201_CREATED
        ).to_dict(),
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def get_current_user_profile_view(
    request: Request,
    current_user: Any
) -> JsonResponse:
    """
    AUTHENTICATED: Get current user's profile
    
    Endpoint: GET /api/users/me/
    Security: Any authenticated user
    """
    controller = await get_user_controller()
    
    user_entity = await controller.get_current_user_profile(
        current_user=current_user,
        context={'request': request}
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=entity_to_dict(user_entity),
            message="Profile retrieved successfully"
        ).to_dict()
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def update_current_user_profile_view(
    request: Request,
    current_user: Any
) -> JsonResponse:
    """
    AUTHENTICATED: Update current user's profile
    
    Endpoint: PUT/PATCH /api/users/me/update/
    Security: Any authenticated user
    """
    controller = await get_user_controller()
    
    # Validate input
    update_data = UserUpdateInputSchema(**request.data)
    
    user_entity = await controller.update_current_user_profile(
        user_data=update_data,
        current_user=current_user,
        context={'request': request}
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=entity_to_dict(user_entity),
            message="Profile updated successfully"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def get_user_by_id_view(
    request: Request,
    user_id: int,
    current_user: Any
) -> JsonResponse:
    """
    OWNER OR ADMIN: Get user by ID
    
    Endpoint: GET /api/users/{id}/
    Security: Users can view themselves, admins can view anyone
    """
    controller = await get_user_controller()
    
    user_entity = await controller.get_user_by_id(
        user_id=user_id,
        current_user=current_user,
        context={'request': request}
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=entity_to_dict(user_entity),
            message="User retrieved successfully"
        ).to_dict()
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def update_user_view(
    request: Request,
    user_id: int,
    current_user: Any
) -> JsonResponse:
    """
    OWNER OR ADMIN: Update user by ID
    
    Endpoint: PUT/PATCH /api/users/{id}/update/
    Security: Users can update themselves, admins can update anyone
    """
    controller = await get_user_controller()
    
    # Validate input
    update_data = UserUpdateInputSchema(**request.data)
    
    user_entity = await controller.update_user(
        user_id=user_id,
        user_data=update_data,
        current_user=current_user,
        context={'request': request}
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=entity_to_dict(user_entity),
            message="User updated successfully"
        ).to_dict()
    )


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def delete_user_view(
    request: Request,
    user_id: int,
    current_user: Any
) -> JsonResponse:
    """
    ADMIN-ONLY: Delete user by ID
    
    Endpoint: DELETE /api/users/{id}/delete/
    Security: Admin only
    """
    controller = await get_user_controller()
    
    success = await controller.delete_user(
        user_id=user_id,
        current_user=current_user,
        context={'request': request}
    )
    
    if success:
        return JsonResponse(
            APIResponse.create_success(
                data={'deleted': True, 'user_id': user_id},
                message="User deleted successfully"
            ).to_dict()
        )
    else:
        raise DomainException("Failed to delete user")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def get_all_users_view(
    request: Request,
    current_user: Any
) -> JsonResponse:
    """
    AUTHENTICATED: Get all users with pagination
    
    Endpoint: GET /api/users/all/
    Security: Any authenticated user
    """
    controller = await get_user_controller()
    
    # Parse query parameters
    page = max(1, int(request.query_params.get('page', 1)))
    per_page = min(100, max(1, int(request.query_params.get('per_page', 20))))
    sort_by = request.query_params.get('sort_by', 'created_at')
    sort_order = request.query_params.get('sort_order', 'desc')
    
    # Build query schema
    query_data = UserQueryInputSchema(
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    users_entities, total_count = await controller.get_all_users(
        validated_data=query_data,
        current_user=current_user,
        context={'request': request}
    )
    
    # Build paginated response
    response_data = create_paginated_response(
        items=entities_to_list(users_entities),
        total_count=total_count,
        page=page,
        per_page=per_page
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=f"Found {total_count} users"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([AllowAny])
@UserAPIExceptionHandler.as_decorator
async def check_email_availability_view(request: Request) -> JsonResponse:
    """
    PUBLIC: Check email availability
    
    Endpoint: GET /api/users/check-email/?email=user@example.com
    Security: Public
    """
    controller = await get_user_controller()
    
    email = request.query_params.get('email')
    if not email:
        raise DomainValidationException(
            message="Email parameter is required",
            field_errors={"email": ["Email is required"]}
        )
    
    email_data = EmailCheckInputSchema(email=email)
    
    result = await controller.check_email_availability(
        validated_data=email_data,
        context={'request': request}
    )
    
    response_data = {
        'email': email,
        'available': result.available,
        'exists': result.exists,
        'suggestion': result.suggestion if hasattr(result, 'suggestion') else None
    }
    
    message = f"Email '{email}' is {'available' if result.available else 'already taken'}"
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=message
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([AllowAny])
@UserAPIExceptionHandler.as_decorator
async def health_check_view(request: Request) -> JsonResponse:
    """
    PUBLIC: Health check endpoint
    
    Endpoint: GET /api/users/health/
    Security: Public
    """
    try:
        controller = await get_user_controller()
        health_status = await controller.health_check()
        
        return JsonResponse(
            APIResponse.create_success(
                data=health_status,
                message="User service is healthy"
            ).to_dict()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse(
            APIResponse.create_error(
                message=f"Service unhealthy: {str(e)}",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            ).to_dict(),
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# ============ MISSING VIEWS (Add these for completeness) ============

@api_view(['GET'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def get_user_by_email_view(
    request: Request,
    current_user: Any
) -> JsonResponse:
    """
    ADMIN-ONLY: Get user by email
    
    Endpoint: GET /api/users/by-email/?email=user@example.com
    Security: Admin only
    """
    controller = await get_user_controller()
    
    email = request.query_params.get('email')
    if not email:
        raise DomainValidationException(
            message="Email parameter is required",
            field_errors={"email": ["Email is required"]}
        )
    
    user_entity = await controller.get_user_by_email(
        email=email,
        current_user=current_user,
        context={'request': request}
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=entity_to_dict(user_entity),
            message="User retrieved successfully"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def get_users_by_role_view(
    request: Request,
    role: str,
    current_user: Any
) -> JsonResponse:
    """
    ADMIN-ONLY: Get users by role
    
    Endpoint: GET /api/users/role/{role}/
    Security: Admin only
    """
    controller = await get_user_controller()
    
    page = max(1, int(request.query_params.get('page', 1)))
    per_page = min(100, max(1, int(request.query_params.get('per_page', 20))))
    
    users_entities, total_count = await controller.get_users_by_role(
        role=role,
        page=page,
        per_page=per_page,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = create_paginated_response(
        items=entities_to_list(users_entities),
        total_count=total_count,
        page=page,
        per_page=per_page,
        role=role
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=f"Found {total_count} users with role '{role}'"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def search_users_view(
    request: Request,
    current_user: Any
) -> JsonResponse:
    """
    ADMIN-ONLY: Search users
    
    Endpoint: GET /api/users/search/?q=search_term
    Security: Admin only
    """
    controller = await get_user_controller()
    
    search_term = request.query_params.get('q', '').strip()
    if not search_term:
        raise DomainValidationException(
            message="Search term is required",
            field_errors={"q": ["Search term cannot be empty"]}
        )
    
    page = max(1, int(request.query_params.get('page', 1)))
    per_page = min(100, max(1, int(request.query_params.get('per_page', 20))))
    
    search_data = UserSearchInputSchema(
        search_term=search_term,
        page=page,
        per_page=per_page
    )
    
    users_entities, total_count = await controller.search_users(
        validated_data=search_data,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = create_paginated_response(
        items=entities_to_list(users_entities),
        total_count=total_count,
        page=page,
        per_page=per_page,
        search_term=search_term
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=f"Found {total_count} matching users"
        ).to_dict()
    )


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
@inject_current_user
async def change_user_status_view(
    request: Request,
    user_id: int,
    current_user: Any
) -> JsonResponse:
    """
    ADMIN-ONLY: Change user status
    
    Endpoint: PATCH /api/users/{id}/status/
    Security: Admin only
    """
    controller = await get_user_controller()
    
    status_value = request.data.get('status')
    if not status_value:
        raise DomainValidationException(
            message="Status is required",
            field_errors={"status": ["Status field is required"]}
        )
    
    user_entity = await controller.change_user_status(
        user_id=user_id,
        status=status_value,
        current_user=current_user,
        context={'request': request}
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=entity_to_dict(user_entity),
            message=f"User status changed to '{status_value}'"
        ).to_dict()
    )


# ============ URL PATTERNS ============

def get_user_url_patterns():
    """
    Generate Django URL patterns for all user views
    
    Design: Centralized URL configuration
    """
    from django.urls import path
    
    urlpatterns = [
        # Public endpoints
        path('register/', register_user_view, name='user-register'),
        path('check-email/', check_email_availability_view, name='check-email'),
        path('health/', health_check_view, name='user-health'),
        
        # Authenticated endpoints
        path('me/', get_current_user_profile_view, name='current-user-profile'),
        path('me/update/', update_current_user_profile_view, name='update-current-user'),
        path('all/', get_all_users_view, name='all-users'),
        
        # User-specific endpoints (owner or admin)
        path('<int:user_id>/', get_user_by_id_view, name='user-by-id'),
        path('<int:user_id>/update/', update_user_view, name='update-user'),
        
        # Admin-only endpoints
        path('admin/create/', create_admin_user_view, name='create-admin-user'),
        path('by-email/', get_user_by_email_view, name='user-by-email'),
        path('role/<str:role>/', get_users_by_role_view, name='users-by-role'),
        path('search/', search_users_view, name='search-users'),
        path('<int:user_id>/status/', change_user_status_view, name='change-user-status'),
        path('<int:user_id>/delete/', delete_user_view, name='delete-user'),
    ]
    
    return urlpatterns