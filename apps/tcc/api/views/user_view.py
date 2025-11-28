from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response  
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from django.core.exceptions import PermissionDenied
import logging

from apps.tcc.usecase.services.users.user_controller import create_user_controller
from .base_view import build_context, get_pagination_params, extract_filters

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([])  # Allow any for registration
async def user_create_view(request: Request) -> Response:
    """User creation endpoint"""
    try:
        controller = await create_user_controller()
        result = await controller.create_user(request.data, build_context(request))
        return Response(
            result.model_dump() if hasattr(result, 'model_dump') else result,
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        logger.error(f"User creation error: {str(e)}")
        return Response(
            {"error": str(e), "message": "User creation failed"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
async def user_profile_view(request: Request) -> Response:
    """User profile operations"""
    try:
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
        
    except Exception as e:
        logger.error(f"User profile operation error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Profile operation failed"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
async def user_detail_view(request: Request, user_id: int) -> Response:
    """User operations by ID"""
    try:
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
        
    except PermissionDenied as e:
        logger.warning(f"Permission denied for user {request.user.id} on user {user_id}: {str(e)}")
        return Response(
            {"error": str(e), "message": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"User detail operation error for user_id {user_id}: {str(e)}")
        return Response(
            {"error": str(e), "message": "User operation failed"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def user_list_view(request: Request) -> Response:
    """User listing with search and filtering"""
    try:
        controller = await create_user_controller()
        page, per_page = get_pagination_params(request)
        
        if search_term := request.query_params.get('search'):
            result = await controller.search_users(search_term, page, per_page, request.user, build_context(request))
        elif role := request.query_params.get('role'):
            result = await controller.get_users_by_role(role, page, per_page, request.user, build_context(request))
        else:
            filters = extract_filters(request)
            result = await controller.get_all_users(filters, page, per_page, request.user, build_context(request))
        
        return Response(
            result.model_dump() if hasattr(result, 'model_dump') else result,
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"User list operation error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Failed to retrieve users"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def user_by_email_view(request: Request) -> Response:
    """Get user by email"""
    try:
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
    except Exception as e:
        logger.error(f"User by email operation error for email {email}: {str(e)}")
        return Response(
            {"error": str(e), "message": "Failed to retrieve user by email"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
async def user_admin_view(request: Request, user_id: int) -> Response:
    """Admin-only user status management"""
    try:
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
    except Exception as e:
        logger.error(f"User admin operation error for user_id {user_id}: {str(e)}")
        return Response(
            {"error": str(e), "message": "Failed to update user status"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
async def user_bulk_view(request: Request) -> Response:
    """Bulk user operations (admin only)"""
    try:
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
    except Exception as e:
        logger.error(f"User bulk operation error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Bulk operation failed"},
            status=status.HTTP_400_BAD_REQUEST
        )