from apps.tcc.api.views.async_utils import async_api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response  
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import status
from django.core.exceptions import PermissionDenied
from asgiref.sync import async_to_sync  # Add this import
from functools import wraps  # Add this import

from apps.tcc.usecase.services.users.user_controller import create_user_controller
from .base_view import build_context, get_pagination_params, extract_filters

# Create a custom decorator for async views
def async_api_view(http_method_names):
    """Custom decorator to handle async views with DRF"""
    def decorator(async_view_func):
        @wraps(async_view_func)
        def sync_wrapper(request, *args, **kwargs):
            return async_to_sync(async_view_func)(request, *args, **kwargs)
        return api_view(http_method_names)(sync_wrapper)
    return decorator


@async_api_view(['POST'])  # Changed from @api_view
@permission_classes([])  # Allow any for registration
async def user_create_view(request: Request) -> Response:
    """User creation endpoint"""
    controller = await create_user_controller()
    result = await controller.create_user(request.data, build_context(request))
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_201_CREATED
    )


@async_api_view(['GET', 'PUT'])  # Changed from @api_view
@permission_classes([AllowAny])
async def user_profile_view(request: Request) -> Response:
    """User profile operations"""
    controller = await create_user_controller()
    
    if request.method == 'GET':
        result = await controller.get_current_user_profile(request.user, build_context(request))
        return Response(
            result.model_dump() if hasattr(result, 'model_dump') else result,
            status=status.HTTP_200_OK
        )
    elif request.method == 'PUT':
        result = await controller.update_current_user_profile(request.data, request.user, build_context(request))
        return Response(
            result.model_dump() if hasattr(result, 'model_dump') else result,
            status=status.HTTP_200_OK
        )


@async_api_view(['GET', 'PUT', 'DELETE'])  # Changed from @api_view
@permission_classes([AllowAny])
async def user_detail_view(request: Request, user_id: int) -> Response:
    """User operations by ID"""
    controller = await create_user_controller()
    
    if request.method == 'GET':
        result = await controller.get_user_by_id(user_id, request.user, build_context(request))
        return Response(
            result.model_dump() if hasattr(result, 'model_dump') else result,
            status=status.HTTP_200_OK
        )
    elif request.method == 'PUT':
        result = await controller.update_user(user_id, request.data, request.user, build_context(request))
        return Response(
            result.model_dump() if hasattr(result, 'model_dump') else result,
            status=status.HTTP_200_OK
        )
    elif request.method == 'DELETE':
        # Only allow users to delete their own account or admin users
        if not request.user.is_staff and request.user.id != user_id:
            raise PermissionDenied("You can only delete your own account")
        result = await controller.delete_user(user_id, request.user, build_context(request))
        return Response(
            result.model_dump() if hasattr(result, 'model_dump') else result,
            status=status.HTTP_200_OK
        )


@async_api_view(['GET'])  # Changed from @api_view
@permission_classes([AllowAny])
async def user_list_view(request: Request) -> Response:
    """User listing with search and filtering"""
    controller = await create_user_controller()
    
    if search_term := request.query_params.get('search'):
        result = await controller.search_users(request.query_params, request.user, build_context(request))
    elif role := request.query_params.get('role'):
        page, per_page = get_pagination_params(request)
        result = await controller.get_users_by_role(role, page, per_page, request.user, build_context(request))
    else:
        result = await controller.get_all_users(request.query_params, request.user, build_context(request))
    
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_200_OK
    )


@async_api_view(['GET'])  # Changed from @api_view
@permission_classes([AllowAny])
async def user_by_email_view(request: Request) -> Response:
    """Get user by email"""
    email = request.query_params.get('email')
    if not email:
        return Response(
            {"error": "Email parameter is required"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    controller = await create_user_controller()
    result = await controller.get_user_by_email(email, request.user, build_context(request))
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_200_OK
    )


@async_api_view(['PATCH'])  # Changed from @api_view
@permission_classes([AllowAny])
async def user_change_status_view(request: Request, user_id: int) -> Response:
    """Change user status"""
    status_value = request.data.get('status')
    if not status_value:
        return Response(
            {"error": "Status is required"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    controller = await create_user_controller()
    result = await controller.change_user_status(user_id, status_value, request.user, build_context(request))
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_200_OK
    )


@async_api_view(['POST'])  # Changed from @api_view
@permission_classes([AllowAny])
async def user_bulk_status_view(request: Request) -> Response:
    """Bulk user status operations"""
    user_ids = request.data.get('user_ids', [])
    status_value = request.data.get('status')
    
    if not user_ids:
        return Response(
            {"error": "user_ids array is required"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    if not status_value:
        return Response(
            {"error": "status is required"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    controller = await create_user_controller()
    result = await controller.bulk_change_status(user_ids, status_value, request.user, build_context(request))
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_200_OK
    )


@async_api_view(['POST'])  # Changed from @api_view
@permission_classes([AllowAny])
async def user_change_password_view(request: Request) -> Response:
    """Change user password"""
    controller = await create_user_controller()
    result = await controller.change_password(request.data, request.user, build_context(request))
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_200_OK
    )


@async_api_view(['POST'])  # Changed from @api_view
@permission_classes([AllowAny])
async def user_verify_password_view(request: Request) -> Response:
    """Verify user password"""
    controller = await create_user_controller()
    result = await controller.verify_password(request.data, build_context(request))
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_200_OK
    )


@async_api_view(['GET'])  # Changed from @api_view
@permission_classes([])  # Public endpoint
async def user_check_email_view(request: Request) -> Response:
    """Check email availability"""
    controller = await create_user_controller()
    result = await controller.check_email_availability(request.query_params, build_context(request))
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_200_OK
    )


@async_api_view(['POST'])  # Changed from @api_view
@permission_classes([])  # Public endpoint
async def user_request_password_reset_view(request: Request) -> Response:
    """Request password reset"""
    controller = await create_user_controller()
    result = await controller.request_password_reset(request.data, build_context(request))
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_200_OK
    )


@async_api_view(['POST'])  # Changed from @api_view
@permission_classes([])  # Public endpoint
async def user_reset_password_view(request: Request) -> Response:
    """Reset password"""
    controller = await create_user_controller()
    result = await controller.reset_password(request.data, build_context(request))
    return Response(
        result.model_dump() if hasattr(result, 'model_dump') else result,
        status=status.HTTP_200_OK
    )