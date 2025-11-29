import logging
from typing import Dict, Any
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.tcc.usecase.services.exceptions.auth_exceptions import AuthExceptionHandler
from apps.core.schemas.input_schemas.auth import (
    LoginInputSchema, RegisterInputSchema, RefreshTokenInputSchema,
    LogoutInputSchema, ForgotPasswordInputSchema, ResetPasswordInputSchema
)
from apps.core.core_validators.decorators import validate_input

logger = logging.getLogger(__name__)

class AuthController(BaseController):
    """
    Complete Controller Layer - All HTTP logic, exception handling, and response formatting
    """

    def __init__(self):
        self.login_uc = None
        self.logout_uc = None
        self.refresh_uc = None
        self.verify_uc = None
        self.register_uc = None
        self.forgot_password_uc = None
        self.reset_password_uc = None

    async def initialize(self):
        """Initialize use cases via dependency injection"""
        from apps.tcc.dependencies.auth_dep import (
            get_login_uc, get_logout_uc, get_refresh_uc, get_verify_uc,
            get_register_uc, get_forgot_password_uc, get_reset_password_uc
        )
        
        self.login_uc = await get_login_uc()
        self.logout_uc = await get_logout_uc()
        self.refresh_uc = await get_refresh_uc()
        self.verify_uc = await get_verify_uc()
        self.register_uc = await get_register_uc()
        self.forgot_password_uc = await get_forgot_password_uc()
        self.reset_password_uc = await get_reset_password_uc()

    # ============ CONTROLLER METHODS WITH COMPLETE LOGIC ============

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(LoginInputSchema)
    async def login(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> APIResponse:
        """Complete login logic with exception handling and response formatting"""
        if not self.login_uc:
            await self.initialize()

        # Execute business logic via use case
        result = await self.login_uc.execute(input_data, None, context or {})
        
        # Format successful response
        return APIResponse.success_response(
            message="Login successful",
            data=result.dict() if hasattr(result, 'dict') else result,
            status_code=200
        )

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(RegisterInputSchema)
    async def register(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> APIResponse:
        """Complete registration logic with exception handling and response formatting"""
        if not self.register_uc:
            await self.initialize()

        result = await self.register_uc.execute(input_data, None, context or {})
        
        return APIResponse.success_response(
            message="Registration successful",
            data=result.dict() if hasattr(result, 'dict') else result,
            status_code=201
        )

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(LogoutInputSchema)
    async def logout(self, input_data: Dict[str, Any], current_user: Any, context: Dict[str, Any] = None) -> APIResponse:
        """Complete logout logic with exception handling and response formatting"""
        if not self.logout_uc:
            await self.initialize()

        result = await self.logout_uc.execute(input_data, current_user, context or {})
        
        return APIResponse.success_response(
            message="Logout successful",
            data=result.dict() if hasattr(result, 'dict') else result,
            status_code=200
        )

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(RefreshTokenInputSchema)
    async def refresh_token(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> APIResponse:
        """Complete token refresh logic with exception handling and response formatting"""
        if not self.refresh_uc:
            await self.initialize()

        result = await self.refresh_uc.execute(input_data, None, context or {})
        
        return APIResponse.success_response(
            message="Token refreshed successfully",
            data=result.dict() if hasattr(result, 'dict') else result,
            status_code=200
        )

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    async def verify_token(self, current_user: Any, context: Dict[str, Any] = None) -> APIResponse:
        """Complete token verification logic with exception handling and response formatting"""
        if not self.verify_uc:
            await self.initialize()

        result = await self.verify_uc.execute({}, current_user, context or {})
        
        return APIResponse.success_response(
            message="Token is valid",
            data=result.dict() if hasattr(result, 'dict') else result,
            status_code=200
        )

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(ForgotPasswordInputSchema)
    async def forgot_password(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> APIResponse:
        """Complete forgot password logic with exception handling and response formatting"""
        if not self.forgot_password_uc:
            await self.initialize()

        result = await self.forgot_password_uc.execute(input_data, None, context or {})
        
        return APIResponse.success_response(
            message="Password reset instructions sent",
            data=result.dict() if hasattr(result, 'dict') else result,
            status_code=200
        )

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(ResetPasswordInputSchema)
    async def reset_password(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> APIResponse:
        """Complete reset password logic with exception handling and response formatting"""
        if not self.reset_password_uc:
            await self.initialize()

        result = await self.reset_password_uc.execute(input_data, None, context or {})
        
        return APIResponse.success_response(
            message="Password reset successfully",
            data=result.dict() if hasattr(result, 'dict') else result,
            status_code=200
        )


async def create_auth_controller() -> AuthController:
    """Factory function for auth controller"""
    controller = AuthController()
    await controller.initialize()
    return controller