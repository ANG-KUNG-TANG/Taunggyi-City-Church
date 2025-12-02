import logging
from typing import Dict, Any, Union
from apps.core.schemas.common.response import APIResponse
from apps.core.schemas.out_schemas.aut_out_schemas import AuthSuccessResponseSchema, ForgotPasswordResponseSchema, LoginResponseSchema, LogoutResponseSchema, RegisterResponseSchema, ResetPasswordResponseSchema, TokenRefreshResponseSchema
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
    Controller Layer - Handles business logic and domain exceptions
    Returns: Domain schema (success) or APIResponse (error from AuthExceptionHandler)
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

    # ============ CONTROLLER METHODS ============
    # Each method returns: domain schema (success) or APIResponse (error)

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(LoginInputSchema)
    async def login(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Union[LoginResponseSchema, APIResponse]:
        """
        Login controller
        Returns: LoginResponseSchema (success) or APIResponse (error)
        """
        if not self.login_uc:
            await self.initialize()
        
        result = await self.login_uc.execute(input_data, None, context or {})
        return result

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(RegisterInputSchema)
    async def register(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Union[RegisterResponseSchema, APIResponse]:
        """
        Register controller
        Returns: RegisterResponseSchema (success) or APIResponse (error)
        """
        if not self.register_uc:
            await self.initialize()

        result = await self.register_uc.execute(input_data, None, context or {})
        return result

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(LogoutInputSchema)
    async def logout(self, input_data: Dict[str, Any], current_user: Any, context: Dict[str, Any] = None) -> Union[LogoutResponseSchema, APIResponse]:
        """
        Logout controller
        Returns: LogoutResponseSchema (success) or APIResponse (error)
        """
        if not self.logout_uc:
            await self.initialize()

        result = await self.logout_uc.execute(input_data, current_user, context or {})
        return result

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(RefreshTokenInputSchema)
    async def refresh_token(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Union[TokenRefreshResponseSchema, APIResponse]:
        """
        Token refresh controller
        Returns: TokenRefreshResponseSchema (success) or APIResponse (error)
        """
        if not self.refresh_uc:
            await self.initialize()

        result = await self.refresh_uc.execute(input_data, None, context or {})
        return result

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    async def verify_token(self, current_user: Any, context: Dict[str, Any] = None) -> Union[AuthSuccessResponseSchema, APIResponse]:
        """
        Token verification controller
        Returns: AuthSuccessResponseSchema (success) or APIResponse (error)
        """
        if not self.verify_uc:
            await self.initialize()

        result = await self.verify_uc.execute({}, current_user, context or {})
        return result

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(ForgotPasswordInputSchema)
    async def forgot_password(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Union[ForgotPasswordResponseSchema, APIResponse]:
        """
        Forgot password controller
        Returns: ForgotPasswordResponseSchema (success) or APIResponse (error)
        """
        if not self.forgot_password_uc:
            await self.initialize()

        result = await self.forgot_password_uc.execute(input_data, None, context or {})
        return result

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(ResetPasswordInputSchema)
    async def reset_password(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Union[ResetPasswordResponseSchema, APIResponse]:
        """
        Reset password controller
        Returns: ResetPasswordResponseSchema (success) or APIResponse (error)
        """
        if not self.reset_password_uc:
            await self.initialize()

        result = await self.reset_password_uc.execute(input_data, None, context or {})
        return result


async def create_auth_controller() -> AuthController:
    """Factory function for auth controller"""
    controller = AuthController()
    await controller.initialize()
    return controller