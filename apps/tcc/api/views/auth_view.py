from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response  
from rest_framework.permissions import IsAuthenticated, AllowAny
import logging

from apps.tcc.usecase.services.auth.auth_controller import create_auth_controller
from .base_view import build_context

logger = logging.getLogger(__name__)

# Global controller instance
_auth_controller = None

async def get_auth_controller():
    """Get or create auth controller singleton"""
    global _auth_controller
    if _auth_controller is None:
        _auth_controller = await create_auth_controller()
    return _auth_controller

# ============ AUTHENTICATION ENDPOINTS ============

@api_view(['POST'])
@permission_classes([AllowAny])
async def login_view(request: Request) -> Response:
    """User login endpoint - Pure HTTP pass-through"""
    controller = await get_auth_controller()
    result = await controller.login(request.data, build_context(request))
    return Response(result.data, status=result.status_code)


@api_view(['POST'])
@permission_classes([AllowAny])
async def register_view(request: Request) -> Response:
    """User registration endpoint - Pure HTTP pass-through"""
    controller = await get_auth_controller()
    result = await controller.register(request.data, build_context(request))
    return Response(result.data, status=result.status_code)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def logout_view(request: Request) -> Response:
    """User logout endpoint - Pure HTTP pass-through"""
    controller = await get_auth_controller()
    result = await controller.logout(
        request.data,
        request.user,
        build_context(request)
    )
    return Response(result.data, status=result.status_code)


@api_view(['POST'])
@permission_classes([AllowAny])
async def refresh_token_view(request: Request) -> Response:
    """Token refresh endpoint - Pure HTTP pass-through"""
    controller = await get_auth_controller()
    result = await controller.refresh_token(request.data, build_context(request))
    return Response(result.data, status=result.status_code)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def verify_token_view(request: Request) -> Response:
    """Token verification endpoint - Pure HTTP pass-through"""
    controller = await get_auth_controller()
    result = await controller.verify_token(request.user, build_context(request))
    return Response(result.data, status=result.status_code)


@api_view(['POST'])
@permission_classes([AllowAny])
async def forgot_password_view(request: Request) -> Response:
    """Forgot password endpoint - Pure HTTP pass-through"""
    controller = await get_auth_controller()
    result = await controller.forgot_password(request.data, build_context(request))
    return Response(result.data, status=result.status_code)


@api_view(['POST'])
@permission_classes([AllowAny])
async def reset_password_view(request: Request) -> Response:
    """Reset password endpoint - Pure HTTP pass-through"""
    controller = await get_auth_controller()
    result = await controller.reset_password(request.data, build_context(request))
    return Response(result.data, status=result.status_code)


# ============ SESSION MANAGEMENT ENDPOINTS ============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def user_sessions_view(request: Request) -> Response:
    """Get user's active sessions - Pure HTTP pass-through"""
    # TODO: Implement when SessionController is available
    from apps.core.schemas.common.response import APIResponse
    result = APIResponse.success_response(
        message="Sessions retrieved successfully",
        data={"sessions": [], "total": 0}
    )
    return Response(result.data, status=result.status_code)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
async def revoke_session_view(request: Request, session_id: str) -> Response:
    """Revoke a specific session - Pure HTTP pass-through"""
    # TODO: Implement when SessionController is available
    from apps.core.schemas.common.response import APIResponse
    result = APIResponse.success_response(message="Session revoked successfully")
    return Response(result.data, status=result.status_code)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def revoke_all_sessions_view(request: Request) -> Response:
    """Revoke all sessions except current - Pure HTTP pass-through"""
    # TODO: Implement when SessionController is available
    from apps.core.schemas.common.response import APIResponse
    result = APIResponse.success_response(message="All other sessions revoked successfully")
    return Response(result.data, status=result.status_code)


# ============ HEALTH CHECK ============

@api_view(['GET'])
@permission_classes([AllowAny])
async def auth_health_check(request: Request) -> Response:
    """Authentication service health check - Pure HTTP pass-through"""
    from apps.core.schemas.common.response import APIResponse
    result = APIResponse.success_response(
        message="Authentication service is healthy",
        data={"service": "auth", "status": "operational"}
    )
    return Response(result.data, status=result.status_code)