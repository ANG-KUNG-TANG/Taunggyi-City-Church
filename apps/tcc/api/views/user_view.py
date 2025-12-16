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
from apps.tcc.usecase.services.users.user_controller import (
    get_user_controller as get_singleton_user_controller,
    create_user_controller as create_user_controller_default
)
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


# ============ CENTRALIZED EXCEPTION HANDLER ============

class UserAPIExceptionHandler:
    """
    Centralized exception handler for ALL user API endpoints
    Converts domain exceptions to proper HTTP responses
    """
    
    # Domain Exception → HTTP Status Code Mapping
    EXCEPTION_MAP = {
        UserNotFoundException: status.HTTP_404_NOT_FOUND,
        UserAlreadyExistsException: status.HTTP_409_CONFLICT,
        DomainValidationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        PasswordValidationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        AuthenticationException: status.HTTP_401_UNAUTHORIZED,
        AuthorizationException: status.HTTP_403_FORBIDDEN,
        AccountLockedException: status.HTTP_423_LOCKED,
        PermissionError: status.HTTP_403_FORBIDDEN,
    }
    
    @classmethod
    def handle_exception(cls, exc: Exception) -> JsonResponse:
        """
        Convert any domain exception to proper API response
        """
        # Handle UserAlreadyExistsException specifically
        if isinstance(exc, UserAlreadyExistsException):
            logger.warning(f"User already exists: {exc}")
            return JsonResponse(
                {
                    "success": False,
                    "message": "User with this email already exists",
                    "field": "email"
                },
                status=status.HTTP_409_CONFLICT
            )
        
        # Log based on exception type
        log_level = logger.error
        if isinstance(exc, (UserNotFoundException, UserAlreadyExistsException)):
            log_level = logger.warning
        elif isinstance(exc, DomainValidationException):
            log_level = logger.info
        
        log_level(f"API Exception: {type(exc).__name__}: {exc}")
        
        # Get HTTP status code
        status_code = cls.EXCEPTION_MAP.get(
            type(exc), 
            getattr(exc, 'status_code', status.HTTP_400_BAD_REQUEST)
        )
        
        # Build error response
        error_data = {
            "success": False,
            "message": getattr(exc, 'user_message', str(exc)),
            "code": getattr(exc, 'error_code', type(exc).__name__.upper()),
        }
        
        # Add details if available
        if hasattr(exc, 'details') and exc.details:
            error_data["details"] = exc.details
        
        # Add field errors for validation exceptions
        if isinstance(exc, (DomainValidationException, PasswordValidationException)):
            if hasattr(exc, 'field_errors') and exc.field_errors:
                error_data["errors"] = exc.field_errors
        
        # Add identifier for specific exceptions
        if isinstance(exc, UserAlreadyExistsException):
            if hasattr(exc, 'email'):
                error_data["email"] = exc.email
        return JsonResponse(error_data, status=status_code)
    
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


# ============ UTILITY FUNCTIONS ============

def get_current_user_from_request(request: Request) -> Optional[Any]:
    """
    Extract current user from request
    Returns a simple object with user attributes expected by controller
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user
        return type('CurrentUser', (), {
            'id': user.id,
            'username': user.username,
            'email': getattr(user, 'email', ''),
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_active': user.is_active,
            'has_perm': lambda perm: user.has_perm(perm),
            'has_perms': lambda perms: all(user.has_perm(p) for p in perms),
        })()
    return None


def entity_to_dict(entity: UserEntity) -> Dict[str, Any]:
    """
    Convert UserEntity to dictionary for API response
    Removes sensitive information
    """
    if not entity:
        return {}
    
    try:
        # Try Pydantic v2 model_dump first
        entity_dict = entity.model_dump()
    except AttributeError:
        # Fallback for Pydantic v1 or dict-like objects
        if hasattr(entity, 'dict'):
            entity_dict = entity.dict()
        elif hasattr(entity, '__dict__'):
            entity_dict = entity.__dict__.copy()
        else:
            return {}
    
    # Remove sensitive fields
    sensitive_fields = ['password', 'password_hash', 'salt', 'tokens', 'refresh_token']
    for field in sensitive_fields:
        entity_dict.pop(field, None)
    
    # Convert dates to ISO format if needed
    date_fields = ['created_at', 'updated_at', 'date_of_birth', 'baptism_date', 'membership_date']
    for field in date_fields:
        if field in entity_dict and entity_dict[field]:
            if hasattr(entity_dict[field], 'isoformat'):
                entity_dict[field] = entity_dict[field].isoformat()
    
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
    """Helper to create standardized paginated response"""
    return {
        'items': items,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page if per_page > 0 else 1,
        **additional_data
    }


async def get_user_controller() -> Any:
    """
    Get user controller instance with fallback
    """
    try:
        return await get_singleton_user_controller()
    except Exception as e:
        logger.error(f"Failed to get user controller: {e}, creating new instance")
        return await create_user_controller_default()


# ============ CREATE OPERATIONS ============

@api_view(['POST'])
@permission_classes([AllowAny])
@UserAPIExceptionHandler.as_decorator
async def create_user_view(request: Request) -> JsonResponse:
    """
    Create a new user (Public registration)
    POST /api/users/
    """
    controller = await get_user_controller()
    
    # Validate input - let DomainValidationException bubble up
    user_data = UserCreateInputSchema(**request.data)
    
    # Call controller - exceptions bubble up to handler
    user_entity = await controller.create_user(
        user_data=user_data,
        current_user=None,  # Public registration
        context={'request': request}
    )
    
    # Success response
    return JsonResponse(
        APIResponse.create_success(
            data=entity_to_dict(user_entity),
            message="User created successfully",
            status_code=status.HTTP_201_CREATED
        ).to_dict(),
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
async def create_admin_user_view(request: Request) -> JsonResponse:
    """
    Create admin user (Admin only)
    POST /api/users/admin/
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
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


# ============ READ OPERATIONS ============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@UserAPIExceptionHandler.as_decorator
async def get_current_user_profile_view(request: Request) -> JsonResponse:
    """
    Get current authenticated user's profile
    GET /api/users/me/
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@UserAPIExceptionHandler.as_decorator
async def get_user_by_id_view(request: Request, user_id: int) -> JsonResponse:
    """
    Get user by ID (Users can view their own, admins can view any)
    GET /api/users/{id}/
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
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


@api_view(['GET'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
async def get_user_by_email_view(request: Request) -> JsonResponse:
    """
    Get user by email (Admin only)
    GET /api/users/by-email/?email=user@example.com
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
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
async def get_all_users_view(request: Request) -> JsonResponse:
    """
    Get all users with pagination (Admin only)
    GET /api/users/?page=1&per_page=20&sort_by=name&sort_order=asc
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    # Parse query parameters
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    sort_by = request.query_params.get('sort_by', 'created_at')
    sort_order = request.query_params.get('sort_order', 'desc')
    
    # Validate pagination
    if page < 1 or per_page < 1 or per_page > 100:
        raise DomainValidationException(
            message="Invalid pagination parameters",
            field_errors={
                "page": ["Page must be >= 1"],
                "per_page": ["Per page must be between 1 and 100"]
            }
        )
    
    query_data = UserQueryInputSchema(
        page=page,
        per_page=per_page,
        sort_by=sort_by.lstrip('-'),
        sort_order='desc' if sort_by.startswith('-') else sort_order
    )
    
    users_entities, total_count = await controller.get_all_users(
        validated_data=query_data,
        current_user=current_user,
        context={'request': request}
    )
    
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
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
async def get_users_by_role_view(request: Request, role: str) -> JsonResponse:
    """
    Get users by role with pagination (Admin only)
    GET /api/users/role/{role}/?page=1&per_page=20
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    
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
async def search_users_view(request: Request) -> JsonResponse:
    """
    Search users with filters (Admin only)
    GET /api/users/search/?q=search_term&page=1&per_page=20
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    search_term = request.query_params.get('q', '').strip()
    if not search_term:
        raise DomainValidationException(
            message="Search term is required",
            field_errors={"q": ["Search term cannot be empty"]}
        )
    
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    
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


# ============ UPDATE OPERATIONS ============

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@UserAPIExceptionHandler.as_decorator
async def update_user_view(request: Request, user_id: int) -> JsonResponse:
    """
    Update user by ID (Owners or Admin only)
    PUT/PATCH /api/users/{id}/
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
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


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@UserAPIExceptionHandler.as_decorator
async def update_current_user_profile_view(request: Request) -> JsonResponse:
    """
    Update current user's profile
    PUT/PATCH /api/users/me/
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
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


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
async def change_user_status_view(request: Request, user_id: int) -> JsonResponse:
    """
    Change user status (Admin only)
    PATCH /api/users/{id}/status/
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
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


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @UserAPIExceptionHandler.as_decorator
# async def change_password_view(request: Request) -> JsonResponse:
#     """
#     Change current user's password
#     POST /api/users/me/change-password/
#     """
#     controller = await get_user_controller()
#     current_user = get_current_user_from_request(request)
    
#     password_data = UserChangePasswordInputSchema(**request.data)
    
#     user_entity = await controller.change_password(
#         validated_data=password_data,
#         current_user=current_user,
#         context={'request': request}
#     )
    
#     return JsonResponse(
#         APIResponse.create_success(
#             data=entity_to_dict(user_entity),
#             message="Password changed successfully"
#         ).to_dict()
#     )


# ============ EMAIL OPERATIONS ============

@api_view(['GET'])
@permission_classes([AllowAny])
@UserAPIExceptionHandler.as_decorator
async def check_email_availability_view(request: Request) -> JsonResponse:
    """
    Check if email is available (Public endpoint)
    GET /api/users/check-email/?email=user@example.com
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
        'exists': result.exists
    }
    
    message = f"Email '{email}' is {'available' if result.available else 'already taken'}"
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=message
        ).to_dict()
    )


# ============ DELETE OPERATIONS ============

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
async def delete_user_view(request: Request, user_id: int) -> JsonResponse:
    """
    Delete user by ID (Admin only)
    DELETE /api/users/{id}/
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
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
        raise DomainException(
            message="Failed to delete user",
            user_message="User deletion failed. Please try again."
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
@UserAPIExceptionHandler.as_decorator
async def bulk_delete_users_view(request: Request) -> JsonResponse:
    """
    Bulk delete users (Admin only)
    POST /api/users/bulk-delete/
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    user_ids = request.data.get('user_ids', [])
    if not user_ids:
        raise DomainValidationException(
            message="User IDs are required",
            field_errors={"user_ids": ["User IDs array cannot be empty"]}
        )
    
    result = await controller.bulk_delete_users(
        user_ids=user_ids,
        current_user=current_user,
        context={'request': request}
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data=result,
            message="Bulk delete operation completed"
        ).to_dict()
    )


# ============ HEALTH CHECK ============

@api_view(['GET'])
@permission_classes([AllowAny])
@UserAPIExceptionHandler.as_decorator
async def health_check_view(request: Request) -> JsonResponse:
    """
    Health check endpoint
    GET /api/users/health/
    """
    try:
        controller = await get_user_controller()
        current_user = get_current_user_from_request(request)
        
        status_msg = "Controller is fully operational"
        if current_user:
            # Test with authenticated user
            await controller.get_current_user_profile(
                current_user=current_user,
                context={'request': request}
            )
        else:
            # Test basic operation WITHOUT using email_exists which has the thread issue
            # Instead, do a simple database query
            from django.db import connection
            from asgiref.sync import sync_to_async
            
            def sync_check_db():
                # Just check if we can connect to the database
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return cursor.fetchone()
            
            # Use thread_sensitive=False to avoid the issue
            await sync_to_async(sync_check_db, thread_sensitive=False)()
            status_msg = "Controller is operational (basic operations)"
        
        return JsonResponse(
            APIResponse.create_success(
                data={
                    'status': 'healthy',
                    'service': 'UserController',
                    'message': status_msg
                },
                message="User controller is working"
            ).to_dict()
        )
    except Exception as e:
        # Don't use the exception handler for health check failures
        logger.error(f"Health check failed: {e}")
        return JsonResponse(
            APIResponse.create_error(
                message=f"Controller health check failed: {str(e)}",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            ).to_dict(),
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
# ============ URL PATTERNS GENERATOR ============

def get_user_url_patterns():
    """
    Return Django URL patterns for all user views
    """
    from django.urls import path
    
    urlpatterns = [
        # Health check
        path('health/', health_check_view, name='user-health-check'),
        
        # CREATE
        path('', create_user_view, name='create-user'),
        path('admin/', create_admin_user_view, name='create-admin-user'),
        
        # READ
        path('me/', get_current_user_profile_view, name='current-user-profile'),
        path('me/update/', update_current_user_profile_view, name='update-current-user'),
        
        path('<int:user_id>/', get_user_by_id_view, name='user-by-id'),
        path('<int:user_id>/update/', update_user_view, name='update-user'),
        path('<int:user_id>/status/', change_user_status_view, name='change-user-status'),
        path('<int:user_id>/delete/', delete_user_view, name='delete-user'),
        
        path('by-email/', get_user_by_email_view, name='user-by-email'),
        path('all/', get_all_users_view, name='all-users'),
        path('role/<str:role>/', get_users_by_role_view, name='users-by-role'),
        path('search/', search_users_view, name='search-users'),
        
        # EMAIL
        path('check-email/', check_email_availability_view, name='check-email'),
        
        # DELETE
        path('bulk-delete/', bulk_delete_users_view, name='bulk-delete-users'),
    ]
    
    return urlpatterns


# ============ API RESPONSE FORMAT ============

class UserAPIResponseBuilder:
    """
    Helper to build standardized API responses for user operations
    """
    
    @staticmethod
    def create_success_response(data: Any, message: str = None, status_code: int = 200) -> JsonResponse:
        """Create standardized success response"""
        return JsonResponse(
            APIResponse.create_success(
                data=data,
                message=message,
                status_code=status_code
            ).to_dict(),
            status=status_code
        )
    
    @staticmethod
    def create_paginated_response(
        items: List[Dict],
        total: int,
        page: int,
        per_page: int,
        message: str = None,
        **kwargs
    ) -> JsonResponse:
        """Create standardized paginated response"""
        response_data = {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if per_page > 0 else 1,
            **kwargs
        }
        
        if not message:
            message = f"Found {total} items"
        
        return UserAPIResponseBuilder.create_success_response(
            data=response_data,
            message=message
        )


# ============ API VERSIONING MIDDLEWARE (Optional) ============

def api_version_middleware(version: str = 'v1'):
    """
    Middleware to add API version to responses
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            response = await func(*args, **kwargs)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content)
                data['api_version'] = version
                response.content = json.dumps(data)
            return response
        return wrapper
    return decorator


# ============ RATE LIMITING DECORATOR (Optional) ============

def rate_limit(requests_per_minute: int = 60):
    """
    Simple rate limiting decorator
    """
    import time
    from collections import defaultdict
    from django.core.cache import cache
    
    requests = defaultdict(list)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            key = f'rate_limit:{client_ip}:{func.__name__}'
            
            # Get current timestamp
            now = time.time()
            
            # Get existing requests from cache
            request_times = cache.get(key, [])
            
            # Remove requests older than 1 minute
            request_times = [t for t in request_times if now - t < 60]
            
            # Check if limit exceeded
            if len(request_times) >= requests_per_minute:
                return JsonResponse(
                    {
                        'error': 'Rate limit exceeded',
                        'message': f'Please wait before making more requests (limit: {requests_per_minute}/minute)'
                    },
                    status=429
                )
            
            # Add current request
            request_times.append(now)
            cache.set(key, request_times, timeout=60)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator