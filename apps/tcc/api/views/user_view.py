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
from apps.core.schemas.common.pagination import PaginatedResponse
from apps.tcc.usecase.services.users.user_controller import (
    get_user_controller as get_singleton_user_controller,
    create_user_controller as create_user_controller_default
)
from apps.tcc.usecase.domain_exception.u_exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException
)
from apps.tcc.usecase.domain_exception.auth_exceptions import AuthenticationException
from apps.core.core_exceptions.domain import DomainValidationException

logger = logging.getLogger(__name__)


def handle_view_exceptions(func):
    """
    Decorator to handle exceptions from controller layer and convert to APIResponse
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except UserNotFoundException as e:
            logger.warning(f"User not found: {e}", exc_info=True)
            return JsonResponse(
                APIResponse.create_error(
                    message=e.user_message if hasattr(e, 'user_message') else str(e),
                    status_code=status.HTTP_404_NOT_FOUND
                ).to_dict(),
                status=status.HTTP_404_NOT_FOUND
            )
        except UserAlreadyExistsException as e:
            logger.warning(f"User already exists: {e}", exc_info=True)
            return JsonResponse(
                APIResponse.create_error(
                    message=e.user_message if hasattr(e, 'user_message') else str(e),
                    status_code=status.HTTP_409_CONFLICT
                ).to_dict(),
                status=status.HTTP_409_CONFLICT
            )
        except DomainValidationException as e:
            logger.warning(f"Validation error: {e}", exc_info=True)
            # Try to get more detailed error information
            error_details = str(e)
            if hasattr(e, '__cause__') and e.__cause__:
                error_details = str(e.__cause__)
            return JsonResponse(
                APIResponse.create_error(
                    message=f"Validation failed: {error_details}",
                    status_code=status.HTTP_400_BAD_REQUEST
                ).to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )
        except AuthenticationException as e:
            logger.warning(f"Authentication error: {e}", exc_info=True)
            return JsonResponse(
                APIResponse.create_error(
                    message=e.user_message if hasattr(e, 'user_message') else str(e),
                    status_code=status.HTTP_401_UNAUTHORIZED
                ).to_dict(),
                status=status.HTTP_401_UNAUTHORIZED
            )
        except PermissionError as e:
            logger.warning(f"Permission error: {e}", exc_info=True)
            return JsonResponse(
                APIResponse.create_error(
                    message=str(e),
                    status_code=status.HTTP_403_FORBIDDEN
                ).to_dict(),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return JsonResponse(
                APIResponse.create_error(
                    message=f"Internal server error: {str(e)}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper


def get_current_user_from_request(request) -> Any:
    """
    Extract current user from request and convert to UserEntity if needed
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        # Convert Django user to UserEntity format expected by controller
        user = request.user
        # Create a simple object with expected attributes
        class CurrentUser:
            def __init__(self, django_user):
                self.id = django_user.id
                self.username = django_user.username
                self.email = getattr(django_user, 'email', '')
                self.is_staff = django_user.is_staff
                self.is_superuser = django_user.is_superuser
                self.is_active = django_user.is_active
                
        return CurrentUser(user)
    return None


def entity_to_dict(entity: UserEntity) -> Dict[str, Any]:
    """
    Convert UserEntity to dictionary for API response
    """
    if not entity:
        return {}
    
    try:
        # Use model_dump for Pydantic v2
        entity_dict = entity.model_dump()
    except AttributeError:
        # Fallback for Pydantic v1 or other types
        if hasattr(entity, 'dict'):
            entity_dict = entity.dict()
        elif hasattr(entity, '__dict__'):
            entity_dict = entity.__dict__
        else:
            return {}
    
    # Remove sensitive information
    sensitive_fields = ['password', 'password_hash', 'salt', 'tokens']
    for field in sensitive_fields:
        entity_dict.pop(field, None)
    
    return entity_dict


def entities_to_list(entities: List[UserEntity]) -> List[Dict[str, Any]]:
    """
    Convert list of UserEntity to list of dictionaries
    """
    if not entities:
        return []
    
    return [entity_to_dict(entity) for entity in entities]


async def get_user_controller():
    """
    Get user controller instance using singleton pattern
    """
    try:
        return await get_singleton_user_controller()
    except Exception as e:
        logger.error(f"Failed to get user controller: {e}")
        # Fallback to creating new instance
        return await create_user_controller_default()


# ============ CREATE Views ============

@api_view(['POST'])
@permission_classes([])
@handle_view_exceptions
async def create_user_view(request: Request) -> JsonResponse:
    """
    Create a new user (Public registration)
    """
    controller = await get_user_controller()
    
    # Validate input schema
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
    
    # Call controller - pass None as current_user for public registration
    user_entity = await controller.create_user(
        user_data=user_data,
        current_user=None,  
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
@permission_classes([])
@handle_view_exceptions
async def get_user_by_id_view(request: Request, user_id: int) -> JsonResponse:
    """
    Get user by ID (Authenticated users can view their own profile, admins can view any)
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    # Call controller - it will handle permission checks
    user_entity = await controller.get_user_by_id(
        user_id=user_id,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message="User retrieved successfully"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([])
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
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user_entity = await controller.get_user_by_email(
        email=email,
        current_user=current_user,
        context={'request': request}
    )
    
    response_data = entity_to_dict(user_entity)
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message="User retrieved successfully"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([])
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
    sort_by = request.query_params.get('sort_by', '-created_at')
    sort_order = 'desc' if sort_by.startswith('-') else 'asc'
    sort_field = sort_by.lstrip('-')
    
    try:
        query_data = UserQueryInputSchema(
            page=page,
            per_page=per_page,
            sort_by=sort_field,
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
    
    # Convert to response
    users_data = entities_to_list(users_entities)
    
    # Create paginated response
    response_data = {
        'items': users_data,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page if per_page > 0 else 1
    }
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=f"Found {total_count} users"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([])
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
        'total_pages': (total_count + per_page - 1) // per_page if per_page > 0 else 1
    }
    
    return JsonResponse(
        APIResponse.create_success(
            data=response_data,
            message=f"Found {total_count} users with role '{role}'"
        ).to_dict()
    )


@api_view(['GET'])
@permission_classes([])
@handle_view_exceptions
async def search_users_view(request: Request) -> JsonResponse:
    """
    Search users with various filters (Admin only)
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    # Build search criteria
    search_term = request.query_params.get('q', '')
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    
    if not search_term:
        return JsonResponse(
            APIResponse.create_error(
                message="Search term (q parameter) is required",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        search_data = UserSearchInputSchema(
            search_term=search_term,
            page=page,
            per_page=per_page
        )
    except Exception as e:
        return JsonResponse(
            APIResponse.create_error(
                message=f"Invalid search parameters: {str(e)}",
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
        'page': page,
        'per_page': per_page,
        'search_term': search_term,
        'total_pages': (total_count + per_page - 1) // per_page if per_page > 0 else 1
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
@permission_classes([])
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

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @handle_view_exceptions
# async def change_password_view(request: Request) -> JsonResponse:
#     """
#     Change current user's password
#     """
#     controller = await get_user_controller()
#     current_user = get_current_user_from_request(request)
    
#     try:
#         password_data = UserChangePasswordInputSchema(**request.data)
#     except Exception as e:
#         return JsonResponse(
#             APIResponse.create_error(
#                 message=f"Invalid password data: {str(e)}",
#                 status_code=status.HTTP_400_BAD_REQUEST
#             ).to_dict(),
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     user_entity = await controller.change_password(
#         validated_data=password_data,
#         current_user=current_user,
#         context={'request': request}
#     )
    
#     response_data = entity_to_dict(user_entity)
#     return JsonResponse(
#         APIResponse.create_success(
#             data=response_data,
#             message="Password changed successfully"
#         ).to_dict()
#     )


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
        # Call controller's check_email_availability method
        result = await controller.check_email_availability(
            validated_data=email_data,
            context={'request': request}
        )
        
        # CheckEmailExistsUseCase returns EmailCheckResponseSchema
        response_data = {
            'email': email,
            'exists': result.exists,
            'available': result.available
        }
        
        return JsonResponse(
            APIResponse.create_success(
                data=response_data,
                message=f"Email '{email}' is {'available' if result.available else 'already taken'}"
            ).to_dict()
        )
        
    except Exception as e:
        # Fallback to direct check if controller method fails
        logger.warning(f"Email check failed: {e}, using fallback")
        from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
        repo = UserRepository()
        exists = await repo.email_exists(email)
        
        response_data = {
            'email': email,
            'exists': exists,
            'available': not exists
        }
        
        return JsonResponse(
            APIResponse.create_success(
                data=response_data,
                message=f"Email '{email}' is {'available' if not exists else 'already taken'}"
            ).to_dict()
        )


# ============ DELETE Views ============

@api_view(['DELETE'])
@permission_classes([])
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


@api_view(['POST'])
@permission_classes([])
@handle_view_exceptions
async def bulk_delete_users_view(request: Request) -> JsonResponse:
    """
    Bulk delete users (Admin only)
    """
    controller = await get_user_controller()
    current_user = get_current_user_from_request(request)
    
    user_ids = request.data.get('user_ids', [])
    if not user_ids:
        return JsonResponse(
            APIResponse.create_error(
                message="User IDs are required",
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_dict(),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # This uses the BulkDeleteUsersUseCase via controller
        result = await controller.bulk_delete_users(
            user_ids=user_ids,
            current_user=current_user,
            context={'request': request}
        )
        
        return JsonResponse(
            APIResponse.create_success(
                data=result,
                message=f"Bulk delete operation completed"
            ).to_dict()
        )
    except Exception as e:
        logger.error(f"Bulk delete failed: {e}")
        # Manual bulk delete as fallback
        from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
        repo = UserRepository()
        
        deleted_count = 0
        failed_users = []
        
        for user_id in user_ids:
            try:
                success = await repo.delete(user_id, current_user, {'request': request})
                if success:
                    deleted_count += 1
                else:
                    failed_users.append(user_id)
            except Exception as delete_error:
                logger.error(f"Failed to delete user {user_id}: {delete_error}")
                failed_users.append(user_id)
        
        result = {
            'deleted': deleted_count > 0,
            'deleted_count': deleted_count,
            'failed_count': len(failed_users),
            'failed_users': failed_users,
            'message': f"Deleted {deleted_count} users. Failed: {len(failed_users)}"
        }
        
        return JsonResponse(
            APIResponse.create_success(
                data=result,
                message=f"Bulk delete completed with {deleted_count} successes and {len(failed_users)} failures"
            ).to_dict()
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
        
        # Try to call a simple method to verify controller works
        current_user = get_current_user_from_request(request)
        if current_user:
            # Try to get current user profile
            await controller.get_current_user_profile(
                current_user=current_user,
                context={'request': request}
            )
            status_msg = "Controller is fully operational"
        else:
            # Try to check email availability as a simple test
            test_email = "test@example.com"
            from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
            repo = UserRepository()
            await repo.email_exists(test_email)
            status_msg = "Controller is operational (basic operations)"
        
        return JsonResponse(
            APIResponse.create_success(
                data={
                    'status': 'healthy', 
                    'controller': 'UserController', 
                    'message': status_msg
                },
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
        # path('users/me/change-password/', change_password_view, name='change-password'),
        
        # EMAIL
        path('users/check-email/', check_email_availability_view, name='check-email'),
        
        # DELETE
        path('users/<int:user_id>/delete/', delete_user_view, name='delete-user'),
        path('users/bulk-delete/', bulk_delete_users_view, name='bulk-delete-users'),
    ]
    
    return urlpatterns


# Factory function for getting controller in views
# async def get_view_controller():
#     """
#     Get controller instance for view usage
#     """
#     return await get_singleton_user_controller()


# # Helper for testing
# async def test_controller_connection():
#     """
#     Test function to verify controller connection
#     """
#     try:
#         controller = await get_user_controller()
#         logger.info("Controller connection test successful")
#         return True
#     except Exception as e:
#         logger.error(f"Controller connection test failed: {e}")
#         return False