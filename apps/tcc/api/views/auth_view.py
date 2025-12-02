from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response  
from rest_framework.permissions import IsAuthenticated, AllowAny
import logging

from apps.tcc.usecase.services.auth.auth_controller import create_auth_controller
from apps.core.schemas.common.response import APIResponse
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

def _wrap_in_api_response(domain_schema, default_message: str, status_code: int = 200) -> dict:
    """
    Wrap domain schema in APIResponse and convert to dict
    Returns: dict representation of APIResponse
    """
    api_response = APIResponse.success(
        message=default_message,
        data=domain_schema.dict() if hasattr(domain_schema, 'dict') else domain_schema,
        status_code=status_code
    )
    return api_response.dict()

def _create_error_response(error: Exception, default_message: str = "Operation failed") -> dict:
    """
    Create error APIResponse and convert to dict
    Returns: dict representation of error APIResponse
    """
    status_code = getattr(error, 'status_code', 500)
    error_message = str(error) if not hasattr(error, 'user_message') else error.user_message
    
    api_response = APIResponse.error(
        message=f"{default_message}: {error_message}",
        data=None,
        status_code=status_code
    )
    return api_response.dict()

# ============ AUTHENTICATION ENDPOINTS ============

@api_view(['POST'])
@permission_classes([AllowAny])
async def login_view(request: Request) -> Response:
    """User login endpoint - wraps LoginResponseSchema in APIResponse"""
    try:
        controller = await get_auth_controller()
        # Controller returns LoginResponseSchema (domain schema)
        domain_schema = await controller.login(request.data, build_context(request))
        
        # View wraps domain schema in APIResponse
        response_data = _wrap_in_api_response(
            domain_schema=domain_schema,
            default_message="Login successful",
            status_code=200
        )
        
        return Response(response_data, status=response_data.get('status_code', 200))
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Login failed")
        return Response(error_data, status=error_data.get('status_code', 500))

@api_view(['POST'])
@permission_classes([AllowAny])
async def register_view(request: Request) -> Response:
    """User registration endpoint - wraps RegisterResponseSchema in APIResponse"""
    try:
        controller = await get_auth_controller()
        domain_schema = await controller.register(request.data, build_context(request))
        
        response_data = _wrap_in_api_response(
            domain_schema=domain_schema,
            default_message="Registration successful",
            status_code=201
        )
        
        return Response(response_data, status=response_data.get('status_code', 201))
    except Exception as e:
        logger.error(f"Register error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Registration failed")
        return Response(error_data, status=error_data.get('status_code', 500))

@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def logout_view(request: Request) -> Response:
    """User logout endpoint - wraps LogoutResponseSchema in APIResponse"""
    try:
        controller = await get_auth_controller()
        domain_schema = await controller.logout(
            request.data,
            request.user,
            build_context(request)
        )
        
        response_data = _wrap_in_api_response(
            domain_schema=domain_schema,
            default_message="Logout successful",
            status_code=200
        )
        
        return Response(response_data, status=response_data.get('status_code', 200))
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Logout failed")
        return Response(error_data, status=error_data.get('status_code', 500))

@api_view(['POST'])
@permission_classes([AllowAny])
async def refresh_token_view(request: Request) -> Response:
    """Token refresh endpoint - wraps TokenRefreshResponseSchema in APIResponse"""
    try:
        controller = await get_auth_controller()
        domain_schema = await controller.refresh_token(request.data, build_context(request))
        
        response_data = _wrap_in_api_response(
            domain_schema=domain_schema,
            default_message="Token refreshed successfully",
            status_code=200
        )
        
        return Response(response_data, status=response_data.get('status_code', 200))
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Token refresh failed")
        return Response(error_data, status=error_data.get('status_code', 500))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def verify_token_view(request: Request) -> Response:
    """Token verification endpoint - wraps AuthSuccessResponseSchema in APIResponse"""
    try:
        controller = await get_auth_controller()
        domain_schema = await controller.verify_token(request.user, build_context(request))
        
        response_data = _wrap_in_api_response(
            domain_schema=domain_schema,
            default_message="Token is valid",
            status_code=200
        )
        
        return Response(response_data, status=response_data.get('status_code', 200))
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Token verification failed")
        return Response(error_data, status=error_data.get('status_code', 500))

@api_view(['POST'])
@permission_classes([AllowAny])
async def forgot_password_view(request: Request) -> Response:
    """Forgot password endpoint - wraps ForgotPasswordResponseSchema in APIResponse"""
    try:
        controller = await get_auth_controller()
        domain_schema = await controller.forgot_password(request.data, build_context(request))
        
        response_data = _wrap_in_api_response(
            domain_schema=domain_schema,
            default_message="Password reset instructions sent",
            status_code=200
        )
        
        return Response(response_data, status=response_data.get('status_code', 200))
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Forgot password failed")
        return Response(error_data, status=error_data.get('status_code', 500))

@api_view(['POST'])
@permission_classes([AllowAny])
async def reset_password_view(request: Request) -> Response:
    """Reset password endpoint - wraps ResetPasswordResponseSchema in APIResponse"""
    try:
        controller = await get_auth_controller()
        domain_schema = await controller.reset_password(request.data, build_context(request))
        
        response_data = _wrap_in_api_response(
            domain_schema=domain_schema,
            default_message="Password reset successfully",
            status_code=200
        )
        
        return Response(response_data, status=response_data.get('status_code', 200))
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Reset password failed")
        return Response(error_data, status=error_data.get('status_code', 500))

# ============ SESSION MANAGEMENT ENDPOINTS ============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def user_sessions_view(request: Request) -> Response:
    """Get user's active sessions - TODO: Implement when SessionController is available"""
    try:
        from apps.core.schemas.common.response import APIResponse
        result = APIResponse.success(
            message="Sessions retrieved successfully",
            data={"sessions": [], "total": 0}
        )
        return Response(result.dict(), status=200)
    except Exception as e:
        logger.error(f"Get sessions error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Get sessions failed")
        return Response(error_data, status=error_data.get('status_code', 500))

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
async def revoke_session_view(request: Request, session_id: str) -> Response:
    """Revoke a specific session - TODO: Implement when SessionController is available"""
    try:
        from apps.core.schemas.common.response import APIResponse
        result = APIResponse.success(message="Session revoked successfully")
        return Response(result.dict(), status=200)
    except Exception as e:
        logger.error(f"Revoke session error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Revoke session failed")
        return Response(error_data, status=error_data.get('status_code', 500))

@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def revoke_all_sessions_view(request: Request) -> Response:
    """Revoke all sessions except current - TODO: Implement when SessionController is available"""
    try:
        from apps.core.schemas.common.response import APIResponse
        result = APIResponse.success(message="All other sessions revoked successfully")
        return Response(result.dict(), status=200)
    except Exception as e:
        logger.error(f"Revoke all sessions error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Revoke all sessions failed")
        return Response(error_data, status=error_data.get('status_code', 500))

# ============ HEALTH CHECK ============

@api_view(['GET'])
@permission_classes([AllowAny])
async def auth_health_check(request: Request) -> Response:
    """Authentication service health check"""
    try:
        from apps.core.schemas.common.response import APIResponse
        result = APIResponse.success(
            message="Authentication service is healthy",
            data={"service": "auth", "status": "operational"}
        )
        return Response(result.dict(), status=200)
    except Exception as e:
        logger.error(f"Health check error: {str(e)}", exc_info=True)
        error_data = _create_error_response(e, "Health check failed")
        return Response(error_data, status=error_data.get('status_code', 500))