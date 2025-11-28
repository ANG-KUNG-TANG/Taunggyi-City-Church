from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response  
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
import logging

from apps.tcc.usecase.services.auth.auth_controller import create_auth_controller
from .base_view import build_context, get_pagination_params, extract_filters

logger = logging.getLogger(__name__)

# ============ AUTHENTICATION ENDPOINTS ============

@api_view(['POST'])
@permission_classes([AllowAny])
async def login_view(request: Request) -> Response:
    """User login endpoint"""
    try:
        controller = await create_auth_controller()
        result = await controller.login(request.data, build_context(request))
        return Response(result.model_dump(), status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Login failed"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
async def register_view(request: Request) -> Response:
    """User registration endpoint"""
    try:
        controller = await create_auth_controller()
        result = await controller.register(request.data, build_context(request))
        return Response(result.model_dump(), status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Registration failed"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def logout_view(request: Request) -> Response:
    """User logout endpoint"""
    try:
        controller = await create_auth_controller()
        result = await controller.logout(
            request.data,
            request.user,
            build_context(request)
        )
        return Response(result.model_dump(), status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Logout failed"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
async def refresh_token_view(request: Request) -> Response:
    """Token refresh endpoint"""
    try:
        controller = await create_auth_controller()
        result = await controller.refresh_token(request.data, build_context(request))
        return Response(result.model_dump(), status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Token refresh failed"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def verify_token_view(request: Request) -> Response:
    """Token verification endpoint"""
    try:
        controller = await create_auth_controller()
        result = await controller.verify_token(request.user, build_context(request))
        return Response(result.model_dump(), status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Token verification failed"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
async def forgot_password_view(request: Request) -> Response:
    """Forgot password endpoint"""
    try:
        controller = await create_auth_controller()
        result = await controller.forgot_password(request.data, build_context(request))
        return Response(result.model_dump(), status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Password reset request failed"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
async def reset_password_view(request: Request) -> Response:
    """Reset password endpoint"""
    try:
        controller = await create_auth_controller()
        result = await controller.reset_password(request.data, build_context(request))
        return Response(result.model_dump(), status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Password reset failed"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


# ============ SESSION MANAGEMENT ENDPOINTS ============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def user_sessions_view(request: Request) -> Response:
    """Get user's active sessions"""
    try:
        # This would typically use a SessionController
        # For now, return a placeholder response
        return Response({
            "message": "Sessions retrieved successfully",
            "sessions": [],
            "total": 0
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"User sessions error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Failed to retrieve sessions"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
async def revoke_session_view(request: Request, session_id: str) -> Response:
    """Revoke a specific session"""
    try:
        # This would typically use a SessionController
        # For now, return a placeholder response
        return Response({
            "message": "Session revoked successfully"
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Revoke session error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Failed to revoke session"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def revoke_all_sessions_view(request: Request) -> Response:
    """Revoke all sessions except current"""
    try:
        # This would typically use a SessionController
        # For now, return a placeholder response
        return Response({
            "message": "All other sessions revoked successfully"
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Revoke all sessions error: {str(e)}")
        return Response(
            {"error": str(e), "message": "Failed to revoke sessions"}, 
            status=status.HTTP_400_BAD_REQUEST
        )