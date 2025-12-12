import logging
from pydantic import ValidationError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.services.auth.auth_controller import create_auth_controller
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    InvalidAuthInputException,
    InvalidCredentialsException,
    AccountInactiveException,
    UnauthenticatedException,
    AuthenticationException
)
from apps.tcc.usecase.domain_exception.u_exceptions import AccountLockedException
from .base_view import build_context

logger = logging.getLogger(__name__)

_auth_controller = None


async def get_auth_controller():
    global _auth_controller
    if _auth_controller is None:
        _auth_controller = await create_auth_controller()
    return _auth_controller


# ----------------------------------------
# HELPER FOR SUCCESS & ERROR
# ----------------------------------------

def success(data, message, status=200):
    api_resp = APIResponse.create_success(
        message=message,
        data=data,
        status_code=status
    )
    return Response(api_resp.to_dict(), status=status)


def error(message, detail=None, status=400):
    api_resp = APIResponse.create_error(
        message=message,
        data=detail,
        status_code=status
    )
    return Response(api_resp.to_dict(), status=status)

# ----------------------------------------
# AUTH ENDPOINTS (PURE VIEW WRAPPING)
# ----------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
async def login_view(request: Request):
    try:
        # Quick validation for empty request
        if not request.data:
            return error(
                message="Login data is required",
                detail={
                    "field_errors": {
                        "general": ["Please provide email and password to login."]
                    }
                },
                status=400
            )
        
        # Check for empty email/password
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '').strip()
        
        if not email and not password:
            return error(
                message="Email and password are required",
                detail={
                    "field_errors": {
                        "email": ["Email is required to login"],
                        "password": ["Password is required to login"]
                    }
                },
                status=400
            )
        elif not email:
            return error(
                message="Email is required",
                detail={
                    "field_errors": {
                        "email": ["Email is required to login"]
                    }
                },
                status=400
            )
        elif not password:
            return error(
                message="Password is required",
                detail={
                    "field_errors": {
                        "password": ["Password is required to login"]
                    }
                },
                status=400
            )
        
        # If we have data, proceed with controller
        controller = await get_auth_controller()
        domain = await controller.login(request.data, build_context(request))
        return success(domain, "Login successful")
        
    except InvalidAuthInputException as e:
        # This is for validation errors from Pydantic or business logic
        return error(
            message=e.user_message or "Invalid login input",
            detail={
                "field_errors": getattr(e, 'field_errors', {}),
                "error_code": getattr(e, 'error_code', 'INVALID_INPUT')
            },
            status=400
        )
        
    except InvalidCredentialsException as e:
        # This is for invalid email/password combination
        return error(
            message="Invalid email or password",
            detail={
                "error_code": getattr(e, 'error_code', 'INVALID_CREDENTIALS')
            },
            status=401
        )
        
    except AccountInactiveException as e:
        return error(
            message="Account is inactive",
            detail={
                "error_code": getattr(e, 'error_code', 'ACCOUNT_INACTIVE')
            },
            status=401
        )
        
    except AccountLockedException as e:
        return error(
            message="Account is locked",
            detail={
                "error_code": getattr(e, 'error_code', 'ACCOUNT_LOCKED'),
                "user_message": getattr(e, 'user_message', None)
            },
            status=423  # 423 Locked
        )
        
    except (UnauthenticatedException, AuthenticationException) as e:
        return error(
            message="Authentication required",
            detail={
                "error_code": getattr(e, 'error_code', 'AUTHENTICATION_REQUIRED')
            },
            status=401
        )
        
    except Exception as e:
        logger.error("Login error", exc_info=True)
        return error(
            message="Login failed",
            detail={
                "error": str(e),
                "error_type": type(e).__name__
            },
            status=500
        )


@api_view(["POST"])
@permission_classes([AllowAny])
async def register_view(request: Request):
    try:
        controller = await get_auth_controller()
        domain = await controller.register(request.data, build_context(request))
        return success(domain, "Registration successful", status=201)
    except ValidationError as e:
        return error("Validation failed", e.errors(), 400)
    except Exception as e:
        logger.error("Register error", exc_info=True)
        return error("Registration failed", str(e), 500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
async def logout_view(request: Request):
    try:
        controller = await get_auth_controller()
        domain = await controller.logout(request.data, request.user, build_context(request))
        return success(domain, "Logout successful")
    except Exception as e:
        logger.error("Logout error", exc_info=True)
        return error("Logout failed", str(e), 500)


@api_view(["POST"])
@permission_classes([AllowAny])
async def refresh_token_view(request: Request):
    try:
        controller = await get_auth_controller()
        domain = await controller.refresh_token(request.data, build_context(request))
        return success(domain, "Token refreshed successfully")
    except Exception as e:
        logger.error("Token refresh error", exc_info=True)
        return error("Token refresh failed", str(e), 500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
async def verify_token_view(request: Request):
    try:
        controller = await get_auth_controller()
        domain = await controller.verify_token(request.user, build_context(request))
        return success(domain, "Token is valid")
    except Exception as e:
        logger.error("Token verification error", exc_info=True)
        return error("Token verification failed", str(e), 500)


@api_view(["POST"])
@permission_classes([AllowAny])
async def forgot_password_view(request: Request):
    try:
        controller = await get_auth_controller()
        domain = await controller.forgot_password(request.data, build_context(request))
        return success(domain, "Password reset instructions sent")
    except Exception as e:
        logger.error("Forgot password error", exc_info=True)
        return error("Forgot password failed", str(e), 500)


@api_view(["POST"])
@permission_classes([AllowAny])
async def reset_password_view(request: Request):
    try:
        controller = await get_auth_controller()
        domain = await controller.reset_password(request.data, build_context(request))
        return success(domain, "Password reset successful")
    except Exception as e:
        logger.error("Reset password error", exc_info=True)
        return error("Reset password failed", str(e), 500)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
async def user_sessions_view(request: Request):
    return Response({"success": True, "data": [], "message": "Not implemented"}, status=200)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
async def revoke_session_view(request: Request, session_id: str):
    return Response({"success": True, "message": "Not implemented"}, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
async def revoke_all_sessions_view(request: Request):
    return Response({"success": True, "message": "Not implemented"}, status=200)