import logging
from typing import Dict, Any

from apps.core.schemas.out_schemas.aut_out_schemas import (
    AuthSuccessResponseSchema, ForgotPasswordResponseSchema,
    LoginResponseSchema, LogoutResponseSchema, RegisterResponseSchema,
    ResetPasswordResponseSchema, TokenRefreshResponseSchema
)

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
    PURE Controller (Delivery Layer)
    - Returns only domain schemas
    - Never returns APIResponse
    - Exceptions propagate to View to be wrapped in APIResponse
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
        """Dependency Injection: Initialize Use Cases"""
        from apps.tcc.usecase.dependencies.auth_dep import (
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

    # ----------------------------------------
    # CONTROLLER METHODS (PURE DOMAIN OUTPUTS)
    # ----------------------------------------

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(LoginInputSchema)
    async def login(self, input_data: Dict[str, Any], context=None) -> LoginResponseSchema:
        if not self.login_uc:
            await self.initialize()
        return await self.login_uc.execute(input_data, None, context or {})

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(RegisterInputSchema)
    async def register(self, input_data: Dict[str, Any], context=None) -> RegisterResponseSchema:
        if not self.register_uc:
            await self.initialize()
        return await self.register_uc.execute(input_data, None, context or {})

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(LogoutInputSchema)
    async def logout(self, input_data: Dict[str, Any], current_user: Any, context=None) -> LogoutResponseSchema:
        if not self.logout_uc:
            await self.initialize()
        return await self.logout_uc.execute(input_data, current_user, context or {})

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(RefreshTokenInputSchema)
    async def refresh_token(self, input_data: Dict[str, Any], context=None) -> TokenRefreshResponseSchema:
        if not self.refresh_uc:
            await self.initialize()
        return await self.refresh_uc.execute(input_data, None, context or {})

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    async def verify_token(self, current_user: Any, context=None) -> AuthSuccessResponseSchema:
        if not self.verify_uc:
            await self.initialize()
        return await self.verify_uc.execute({}, current_user, context or {})

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(ForgotPasswordInputSchema)
    async def forgot_password(self, input_data: Dict[str, Any], context=None) -> ForgotPasswordResponseSchema:
        if not self.forgot_password_uc:
            await self.initialize()
        return await self.forgot_password_uc.execute(input_data, None, context or {})

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(ResetPasswordInputSchema)
    async def reset_password(self, input_data: Dict[str, Any], context=None) -> ResetPasswordResponseSchema:
        if not self.reset_password_uc:
            await self.initialize()
        return await self.reset_password_uc.execute(input_data, None, context or {})


async def create_auth_controller() -> AuthController:
    controller = AuthController()
    await controller.initialize()
    return controller
