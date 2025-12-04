import logging
from typing import Dict, Any, List, Optional
from functools import wraps

from django.http import HttpRequest, JsonResponse
from rest_framework.request import Request
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.core.cache import cache as django_cache

from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema,
    UserUpdateInputSchema,
    UserQueryInputSchema,
    UserSearchInputSchema,
    EmailCheckInputSchema,
    UserChangePasswordInputSchema,
)
from apps.tcc.usecase.entities.users_entity import UserEntity
from apps.core.cache.async_cache import AsyncCache

# Import the response schemas from the provided file
from apps.core.schemas.common.response import APIResponse
from apps.core.schemas.common.pagination import PaginatedResponse

# Import controller factory functions
from apps.tcc.usecase.services.users.user_controller import (
    create_user_controller_default,
    get_singleton_user_controller
)

# Import decorators (optional, for direct validation if needed)
from apps.core.schemas.validator.user_deco import (
    validate_user_create,
    validate_user_update,
    validate_user_query,
    validate_user_search,
    validate_change_password,
    validate_email_check,
)

logger = logging.getLogger(__name__)


class DjangoAsyncCacheAdapter(AsyncCache):
    """Adapter to use Django cache with AsyncCache interface"""
    
    async def get(self, key: str):
        return django_cache.get(key)
    
    async def set(self, key: str, value: Any, timeout: int = None):
        django_cache.set(key, value, timeout)
    
    async def delete(self, key: str):
        django_cache.delete(key)
    
    async def exists(self, key: str) -> bool:
        return django_cache.get(key) is not None


def handle_view_exceptions(func):
    """
    Decorator to handle exceptions from controller layer and convert to APIResponse
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"View error in {func.__name__}: {e}", exc_info=True)
            
            # Map domain exceptions to appropriate HTTP responses
            error_type = type(e).__name__
            
            if error_type == 'AuthenticationException':
                return JsonResponse(
                    APIResponse.create_error(
                        message=str(e),
                        status_code=status.HTTP_401_UNAUTHORIZED
                    ).to_dict(),
                    status=status.HTTP_401_UNAUTHORIZED
                )
            elif error_type == 'DomainValidationError':
                return JsonResponse(
                    APIResponse.create_error(
                        message=str(e),
                        status_code=status.HTTP_400_BAD_REQUEST
                    ).to_dict(),
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif error_type == 'UserNotFoundError':
                return JsonResponse(
                    APIResponse.create_error(
                        message=str(e),
                        status_code=status.HTTP_404_NOT_FOUND
                    ).to_dict(),
                    status=status.HTTP_404_NOT_FOUND
                )
            elif error_type == 'UserAlreadyExistsError':
                return JsonResponse(
                    APIResponse.create_error(
                        message=str(e),
                        status_code=status.HTTP_409_CONFLICT
                    ).to_dict(),
                    status=status.HTTP_409_CONFLICT
                )
            elif error_type == 'PermissionDenied':
                return JsonResponse(
                    APIResponse.create_error(
                        message=str(e),
                        status_code=status.HTTP_403_FORBIDDEN
                    ).to_dict(),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Generic error
            return JsonResponse(
                APIResponse.create_error(
                    message="Internal server error",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper


def get_current_user_from_request(request) -> Any:
    """
    Extract current user from request
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


def entity_to_dict(entity: UserEntity) -> Dict[str, Any]:
    """
    Convert UserEntity to dictionary for API response
    """
    if not entity:
        return {}
    
    # Convert entity to dict, excluding sensitive fields
    try:
        # Try model_dump() for Pydantic v2
        entity_dict = entity.model_dump()
    except AttributeError:
        # Fallback to dict() for Pydantic v1
        entity_dict = entity.dict()
    
    # Remove sensitive information
    sensitive_fields = ['password', 'password_hash', 'salt', 'tokens']
    for field in sensitive_fields:
        entity_dict.pop(field, None)
    
    return entity_dict


def entities_to_list(entities: List[UserEntity]) -> List[Dict[str, Any]]:
    """
    Convert list of UserEntity to list of dictionaries
    """
    return [entity_to_dict(entity) for entity in entities if entity]


async def get_user_controller(cache_enabled: bool = True):
    """
    Get user controller instance
    """
    if cache_enabled:
        # Create controller with cache
        return await create_user_controller_default()
    else:
        # Create controller without cache
        return await create_user_controller_default()


# ============ CREATE Views ============

@api_view(['POST'])
@permission_classes([IsAdminUser])
@handle_view_exceptions
async def create_user_view(request: Request) -> JsonResponse:
    """
    Create a new user (Admin only)
    """
    controller = await get_user_controller()
    
    # Extract data from request
    try:
        user_data = UserCreateInputSchema(**request.data)
    except Exception as e:
        return JsonResponse(
            APIResponse.create_error(
                message=f"Invalid input data: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Call controller
    user_entity = await controller.create_user(
        user_data=user_data,
        context={'request': request}
    )
    
    # Convert to response
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            message="User created successfully",
            data=response_data,
            status_code=status.HTTP_201_CREATED
        ).to_dict(),
        status=status.HTTP_201_CREATED
    )


# ============ READ Views ============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@handle_view_exceptions
async def get_user_by_id_view(request: Request, user_id: int) -> JsonResponse:
    """
    Get user by ID (Authenticated users only)
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    # Check permission (user can view their own profile or admin can view any)
    if not current_user.is_staff and current_user.id != user_id:
        return JsonResponse(
            APIResponse.create_error(
                message="You can only view your own profile",
                status_code=status.HTTP_403_FORBIDDEN
            ).to_dict(),
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Call controller
    user_entity = await controller.get_user_by_id(
        user_id=user_id,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            data=response_data
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([IsAdminUser])
@handle_view_exceptions
async def get_user_by_email_view(request: Request) -> JsonResponse:
    """
    Get user by email (Admin only)
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    email = request.query_params.get('email')
    if not email:
        return JsonResponse(
            APIResponse.create_error(
                message="Email parameter is required",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
        )
    
    user_entity = await controller.get_user_by_email(
        email=email,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            data=response_data
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([IsAdminUser])
@handle_view_exceptions
async def get_all_users_view(request: Request) -> JsonResponse:
    """
    Get all users with pagination (Admin only)
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    # Extract query parameters
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    sort_by = request.query_params.get('sort_by', 'created_at')
    sort_order = request.query_params.get('sort_order', 'desc')
    
    try:
        query_data = UserQueryInputSchema(
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
    except Exception as e:
        return JsonResponse(
            APIResponse.create_error(
                message=f"Invalid query parameters: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Call controller
    users_entities, total_count = await controller.get_all_users(
        validated_data=query_data,
        current_user=current_user,
        context={'request': request}
    )
    
    # Convert to response using PaginatedResponse
    users_data = entities_to_list(users_entities)
    
    # Create paginated response
    response_data = {
        'items': users_data,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    }
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=f"Found {total_count} users"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([IsAdminUser])
@handle_view_exceptions
async def get_users_by_role_view(request: Request, role: str) -> JsonResponse:
    """
    Get users by role (Admin only)
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
    
    users_data = entities_to_list(users_entities)
    
    # Create paginated response
    response_data = {
        'items': users_data,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'role': role,
        'total_pages': (total_count + per_page - 1) // per_page
    }
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=f"Found {total_count} users with role '{role}'"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([IsAdminUser])
@handle_view_exceptions
async def search_users_view(request: Request) -> JsonResponse:
    """
    Search users with various filters (Admin only)
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    # Build search criteria from query parameters
    search_criteria = {}
    for param in ['q', 'name', 'email', 'role', 'status']:
        value = request.query_params.get(param)
        if value:
            search_criteria[param] = value
    
    if not search_criteria:
        return JsonResponse(
            APIResponse.create_error(
                message="At least one search criteria is required",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Add pagination
    search_criteria['page'] = int(request.query_params.get('page', 1))
    search_criteria['per_page'] = int(request.query_params.get('per_page', 20))
    
    try:
        search_data = UserSearchInputSchema(**search_criteria)
    except Exception as e:
        return JsonResponse(
            APIResponse.create_error(
                message=f"Invalid search criteria: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    users_entities, total_count = await controller.search_users(
        validated_data=search_data,
        current_user=current_user,
        context={'request': request}
    )
    
    users_data = entities_to_list(users_entities)
    
    # Create paginated response
    response_data = {
        'items': users_data,
        'total': total_count,
        'page': search_criteria['page'],
        'per_page': search_criteria['per_page'],
        'criteria': search_criteria,
        'total_pages': (total_count + search_criteria['per_page'] - 1) // search_criteria['per_page']
    }
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=f"Found {total_count} matching users"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@handle_view_exceptions
async def get_current_user_profile_view(request: Request) -> JsonResponse:
    """
    Get current authenticated user's profile
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    if not current_user:
        return JsonResponse(
            APIResponse.create_error(
                message="Authentication required",
                status_code=status.HTTP_401_UNAUTHORIZED
            ).to_dict(),
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    user_entity = await controller.get_current_user_profile(
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message="User profile retrieved successfully"
        ).to_dict()
    )


# ============ UPDATE Views ============

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@handle_view_exceptions
async def update_user_view(request: Request, user_id: int) -> JsonResponse:
    """
    Update user by ID (Owners or Admin only)
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    # Check permission
    if not current_user.is_staff and current_user.id != user_id:
        return JsonResponse(
            APIResponse.create_error(
                message="You can only update your own profile",
                status_code=status.HTTP_403_FORBIDDEN
            ).to_dict(),
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Extract update data
    try:
        update_data = UserUpdateInputSchema(**request.data)
    except Exception as e:
        return JsonResponse(
            APIResponse.create_error(
                message=f"Invalid update data: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user_entity = await controller.update_user(
        user_id=user_id,
        user_data=update_data,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message="User updated successfully"
        ).to_dict()
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@handle_view_exceptions
async def update_current_user_profile_view(request: Request) -> JsonResponse:
    """
    Update current user's profile
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    if not current_user:
        return JsonResponse(
            APIResponse.create_error(
                message="Authentication required",
                status_code=status.HTTP_401_UNAUTHORIZED
            ).to_dict(),
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        update_data = UserUpdateInputSchema(**request.data)
    except Exception as e:
        return JsonResponse(
            APIResponse.create_error(
                message=f"Invalid update data: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user_entity = await controller.update_current_user_profile(
        user_data=update_data,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message="Profile updated successfully"
        ).to_dict()
    )


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
@handle_view_exceptions
async def change_user_status_view(request: Request, user_id: int) -> JsonResponse:
    """
    Change user status (Admin only)
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    status_value = request.data.get('status')
    if not status_value:
        return JsonResponse(
            APIResponse.create_error(
                message="Status is required",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user_entity = await controller.change_user_status(
        user_id=user_id,
        status=status_value,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=f"User status changed to '{status_value}'"
        ).to_dict()
    )


# ============ PASSWORD Views ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@handle_view_exceptions
async def change_password_view(request: Request) -> JsonResponse:
    """
    Change current user's password
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    if not current_user:
        return JsonResponse(
            APIResponse.create_error(
                message="Authentication required",
                status_code=status.HTTP_401_UNAUTHORIZED
            ).to_dict(),
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        password_data = UserChangePasswordInputSchema(**request.data)
    except Exception as e:
        return JsonResponse(
            APIResponse.create_error(
                message=f"Invalid password data: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user_entity = await controller.change_password(
        validated_data=password_data,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message="Password changed successfully"
        ).to_dict()
    )


# ============ EMAIL Views ============

@api_view(['GET'])
@handle_view_exceptions
async def check_email_availability_view(request: Request) -> JsonResponse:
    """
    Check if email is available (Public endpoint)
    """
    controller = await get_user_controller()
    
    email = request.query_params.get('email')
    if not email:
        return JsonResponse(
            APIResponse.create_error(
                message="Email parameter is required",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        email_data = EmailCheckInputSchema(email=email)
    except Exception as e:
        return JsonResponse(
            APIResponse.create_error(
                message=f"Invalid email format: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    is_available = await controller.check_email_availability(
        validated_data=email_data,
        context={'request': request}
    )
    
    return JsonResponse(
        APIResponse.create_success(
            data={'available': is_available, 'email': email},
            message=f"Email '{email}' is {'available' if is_available else 'already taken'}"
        ).to_dict()
    )


# ============ DELETE Views ============

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
@handle_view_exceptions
async def delete_user_view(request: Request, user_id: int) -> JsonResponse:
    """
    Delete user by ID (Admin only)
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
        return JsonResponse(
            APIResponse.create_error(
                message="Failed to delete user",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            ).to_dict(),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============ HEALTH CHECK Views ============

@api_view(['GET'])
@handle_view_exceptions
async def health_check_view(request: Request) -> JsonResponse:
    """
    Health check endpoint to verify controller is working
    """
    try:
        controller = await get_user_controller()
        
        # Try to get the controller's status
        if hasattr(controller, '_dependency_container'):
            status_msg = "Controller initialized"
        else:
            status_msg = "Controller created"
        
        return JsonResponse(
            APIResponse.create_success(
                data={'status': 'healthy', 'controller': 'UserController', 'message': status_msg},
                message="User controller is working"
            ).to_dict()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse(
            APIResponse.create_error(
                message=f"Controller health check failed: {str(e)}",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            ).to_dict(),
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# ============ URL Patterns Helper ============

def get_user_url_patterns():
    """
    Return Django URL patterns for all user views
    """
    from django.urls import path
    
    urlpatterns = [
        # Health check
        path('health/', health_check_view, name='user-health-check'),
        
        # CREATE
        path('users/', create_user_view, name='create-user'),
        
        # READ
        path('users/me/', get_current_user_profile_view, name='current-user-profile'),
        path('users/<int:user_id>/', get_user_by_id_view, name='user-by-id'),
        path('users/by-email/', get_user_by_email_view, name='user-by-email'),
        path('users/all/', get_all_users_view, name='all-users'),
        path('users/role/<str:role>/', get_users_by_role_view, name='users-by-role'),
        path('users/search/', search_users_view, name='search-users'),
        
        # UPDATE
        path('users/<int:user_id>/update/', update_user_view, name='update-user'),
        path('users/me/update/', update_current_user_profile_view, name='update-current-user'),
        path('users/<int:user_id>/status/', change_user_status_view, name='change-user-status'),
        path('users/me/change-password/', change_password_view, name='change-password'),
        
        # EMAIL
        path('users/check-email/', check_email_availability_view, name='check-email'),
        
        # DELETE
        path('users/<int:user_id>/delete/', delete_user_view, name='delete-user'),
    ]
    
    return urlpatterns


# Factory function for getting controller in views
async def get_view_controller():
    """
    Get controller instance for view usage
    """
    return await get_singleton_user_controller()