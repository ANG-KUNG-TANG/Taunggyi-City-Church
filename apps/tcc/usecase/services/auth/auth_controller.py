import logging
from typing import Dict, Any

from apps.core.schemas.out_schemas.aut_out_schemas import (
     LoginResponseSchema, LogoutResponseSchema, 
    TokenRefreshResponseSchema, ForgotPasswordResponseSchema,
    ResetPasswordResponseSchema, AuthSuccessResponseSchema,
    RegisterResponseSchema,
)

from apps.tcc.usecase.domain_exception.auth_exceptions import InvalidAuthInputException
from apps.tcc.usecase.services.auth.base_controller import BaseController
# REMOVE THIS IMPORT: from apps.tcc.usecase.services.exceptions.auth_exceptions import AuthExceptionHandler
from apps.core.core_validators.decorators import validate_input
from apps.tcc.usecase.dependencies.auth_dep import (
    get_login_uc, get_logout_uc, get_refresh_uc,
    get_forgot_password_uc, get_reset_password_uc,
    get_verify_token_uc, 
)

logger = logging.getLogger(__name__)


class AuthController(BaseController):
    """
    PURE Controller (Delivery Layer)
    - Returns only domain schemas
    - Exceptions propagate to View to be wrapped in APIResponse
    """

    def __init__(self):
        super().__init__()
        self._initialized = False
        self.login_uc = None
        self.logout_uc = None
        self.refresh_uc = None
        self.forgot_password_uc = None
        self.reset_password_uc = None
        self.verify_token_uc = None  

    async def initialize(self):
        """Initialize all use cases (dependency injection)"""
        if self._initialized:
            return
            
        try:
            self.login_uc = await get_login_uc()
            self.logout_uc = await get_logout_uc()
            self.refresh_uc = await get_refresh_uc()
            self.forgot_password_uc = await get_forgot_password_uc()
            self.reset_password_uc = await get_reset_password_uc()
            self.verify_token_uc = await get_verify_token_uc()  
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize AuthController: {e}")
            raise

    # ----------------------------------------
    # CONTROLLER METHODS (PURE DOMAIN OUTPUTS)
    # ----------------------------------------

    @BaseController.handle_exceptions
    async def login(self, input_data: Dict[str, Any], context=None) -> LoginResponseSchema:
        """Handle user login with better error reporting"""
        if not self._initialized:
            await self.initialize()
        
        try:
            logger.info(f"Login attempt for email: {input_data.get('email', 'unknown')}")
            result = await self.login_uc.execute(input_data, None, context or {})
            logger.info(f"Login successful for email: {input_data.get('email', 'unknown')}")
            return result
        except InvalidAuthInputException as e:
            # Log more details about invalid auth
            logger.warning(f"Invalid login attempt: {e.user_message} for {input_data.get('email')}")
            raise
        except Exception as e:
            logger.error(f"Unexpected login error: {e}", exc_info=True)
            # Wrap unexpected errors
            raise InvalidAuthInputException(
                field_errors={"general": ["Login service error"]},
                user_message="Unable to process login request",
                operation_id=context.get('operation_id') if context else None
            )
            
    @BaseController.handle_exceptions
    async def logout(self, input_data: Dict[str, Any], 
                     current_user: Any, context=None) -> LogoutResponseSchema:
        """Handle user logout"""
        if not self._initialized:
            await self.initialize()
        return await self.logout_uc.execute(input_data, current_user, context or {})

    @BaseController.handle_exceptions
    async def refresh_token(self, input_data: Dict[str, Any], 
                           context=None) -> TokenRefreshResponseSchema:
        """Refresh access token"""
        if not self._initialized:
            await self.initialize()
        return await self.refresh_uc.execute(input_data, None, context or {})

    @BaseController.handle_exceptions
    async def forgot_password(self, input_data: Dict[str, Any], 
                             context=None) -> ForgotPasswordResponseSchema:
        """Handle forgot password request"""
        if not self._initialized:
            await self.initialize()
        return await self.forgot_password_uc.execute(input_data, None, context or {})

    @BaseController.handle_exceptions
    async def reset_password(self, input_data: Dict[str, Any], 
                            context=None) -> ResetPasswordResponseSchema:
        """Handle password reset"""
        if not self._initialized:
            await self.initialize()
        return await self.reset_password_uc.execute(input_data, None, context or {})

    @BaseController.handle_exceptions
    async def verify_token(self, current_user: Any, 
                          context=None) -> AuthSuccessResponseSchema:
        """Verify if token is still valid using VerifyTokenUseCase"""
        if not self._initialized:
            await self.initialize()
        
        # Use the verify token use case instead of hardcoding
        # Pass empty data since verify token doesn't need input
        return await self.verify_token_uc.execute(None, current_user, context or {})


async def create_auth_controller() -> AuthController:
    """Factory function to create and initialize AuthController"""
    controller = AuthController()
    await controller.initialize()
    return controller

# @BaseController.handle_exceptions
    # @AuthExceptionHandler.handle_auth_exceptions
    # async def change_password(self, input_data: Dict[str, Any], 
    #                           current_user: Any, 
    #                           context=None) -> ChangePasswordResponseSchema:
    #     """Handle password change"""
    #     if not self._initialized:
    #         await self.initialize()
    #     if not hasattr(self, 'change_password_uc'):
    #         self.change_password_uc = await get_change_password_uc()
    #     return await self.change_password_uc.execute(input_data, current_user, context or {})
    