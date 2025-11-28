import logging
from typing import Dict, Any, Optional
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.tcc.usecase.services.exceptions.auth_exceptions import AuthExceptionHandler
from apps.core.schemas.input_schemas.auth import (
    LoginInputSchema, RegisterInputSchema, RefreshTokenInputSchema,
    LogoutInputSchema, ForgotPasswordInputSchema, ResetPasswordInputSchema
)
from apps.core.schemas.out_schemas.aut_out_schemas import (
    LoginResponseSchema, RegisterResponseSchema, TokenRefreshResponseSchema,
    LogoutResponseSchema, PasswordResetResponseSchema, AuthSuccessResponseSchema
)
from apps.core.core_validators.decorators import validate_input

logger = logging.getLogger(__name__)


class AuthController(BaseController):
    """
    Authentication Controller with input validation and standardized output schemas
    """

    def __init__(self):
        # Initialize use cases as None, will be set via dependency injection
        self.login_uc = None
        self.logout_uc = None
        self.refresh_uc = None
        self.verify_uc = None
        self.auth_service = None

    async def initialize(self):
        """Initialize use cases using dependency injection"""
        from apps.tcc.dependencies.auth_dep import (
            get_login_uc, get_logout_uc, get_refresh_uc, get_verify_uc,
            get_auth_service
        )
        
        self.login_uc = await get_login_uc()
        self.logout_uc = await get_logout_uc()
        self.refresh_uc = await get_refresh_uc()
        self.verify_uc = await get_verify_uc()
        self.auth_service = await get_auth_service()

    # LOGIN Operation
    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(LoginInputSchema)
    async def login(
        self, 
        input_data: LoginInputSchema, 
        context: Dict[str, Any] = None
    ) -> LoginResponseSchema:
        """
        User login with email and password
        """
        if not self.login_uc:
            await self.initialize()

        result = await self.login_uc.execute(input_data.model_dump(), None, context or {})
        return LoginResponseSchema(**result.model_dump() if hasattr(result, 'model_dump') else result)

    # REGISTER Operation
    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(RegisterInputSchema)
    async def register(
        self, 
        input_data: RegisterInputSchema, 
        context: Dict[str, Any] = None
    ) -> RegisterResponseSchema:
        """
        User registration
        """
        # Note: You'll need to create a RegisterUseCase or use CreateUserUseCase
        # For now, this is a placeholder
        from apps.tcc.dependencies.auth_dep import get_register_uc
        register_uc = await get_register_uc()
        result = await register_uc.execute(input_data.model_dump(), None, context or {})
        return RegisterResponseSchema(**result.model_dump() if hasattr(result, 'model_dump') else result)

    # LOGOUT Operation  
    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(LogoutInputSchema)
    async def logout(
        self,
        input_data: LogoutInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> LogoutResponseSchema:
        """
        User logout with token revocation
        """
        if not self.logout_uc:
            await self.initialize()

        result = await self.logout_uc.execute(input_data.model_dump(), current_user, context or {})
        return LogoutResponseSchema(**result.model_dump() if hasattr(result, 'model_dump') else result)

    # REFRESH Operation
    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(RefreshTokenInputSchema)
    async def refresh_token(
        self, 
        input_data: RefreshTokenInputSchema, 
        context: Dict[str, Any] = None
    ) -> TokenRefreshResponseSchema:
        """
        Refresh access token using refresh token
        """
        if not self.refresh_uc:
            await self.initialize()

        result = await self.refresh_uc.execute(input_data.model_dump(), None, context or {})
        return TokenRefreshResponseSchema(**result.model_dump() if hasattr(result, 'model_dump') else result)

    # VERIFY Operation
    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    async def verify_token(
        self,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> AuthSuccessResponseSchema:
        """
        Verify token validity and get user data
        """
        if not self.verify_uc:
            await self.initialize()

        result = await self.verify_uc.execute({}, current_user, context or {})
        return AuthSuccessResponseSchema(**result.model_dump() if hasattr(result, 'model_dump') else result)

    # PASSWORD RESET Operations
    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(ForgotPasswordInputSchema)
    async def forgot_password(
        self,
        input_data: ForgotPasswordInputSchema,
        context: Dict[str, Any] = None
    ) -> PasswordResetResponseSchema:
        """
        Request password reset
        """
        # Note: You'll need to create a ForgotPasswordUseCase
        # For now, this is a placeholder
        return PasswordResetResponseSchema(message="Password reset instructions sent to your email")

    @BaseController.handle_exceptions
    @AuthExceptionHandler.handle_auth_exceptions
    @validate_input(ResetPasswordInputSchema)
    async def reset_password(
        self,
        input_data: ResetPasswordInputSchema,
        context: Dict[str, Any] = None
    ) -> PasswordResetResponseSchema:
        """
        Reset password with token
        """
        # Note: You'll need to create a ResetPasswordUseCase
        # For now, this is a placeholder
        return PasswordResetResponseSchema(message="Password reset successfully")

    # DIRECT SERVICE OPERATIONS
    async def revoke_token_direct(
        self,
        token: str,
        user_id: Optional[int] = None,
        context: Dict[str, Any] = None
    ) -> LogoutResponseSchema:
        """
        Direct token revocation using AsyncAuthDomainService
        """
        if not self.auth_service:
            await self.initialize()

        try:
            success = await self.auth_service.revoke_token_async(token, user_id)
            
            if success:
                return LogoutResponseSchema(message="Token revoked successfully")
            else:
                # For error cases, we still return the schema but with appropriate message
                return LogoutResponseSchema(message="Token revocation failed")
                
        except Exception as e:
            logger.error(f"Direct token revocation failed: {str(e)}")
            return LogoutResponseSchema(message="Token revocation error")


# Factory function
async def create_auth_controller() -> AuthController:
    """Create and initialize auth controller using dependency injection"""
    controller = AuthController()
    await controller.initialize()
    return controller