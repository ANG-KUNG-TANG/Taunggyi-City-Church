import logging
import traceback
from typing import Dict, Any

from apps.core.schemas.out_schemas.aut_out_schemas import (
    LoginResponseSchema, LogoutResponseSchema, 
    TokenRefreshResponseSchema, ForgotPasswordResponseSchema,
    ResetPasswordResponseSchema, AuthSuccessResponseSchema,
    RegisterResponseSchema,
)

from apps.tcc.usecase.domain_exception.auth_exceptions import AccountInactiveException, InvalidAuthInputException
from apps.tcc.usecase.domain_exception.u_exceptions import AccountLockedException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth import auth_service
from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.core.core_validators.decorators import validate_input
from apps.tcc.usecase.dependencies.auth_dep import (
    get_login_uc, get_logout_uc, get_refresh_uc,
    get_forgot_password_uc, get_reset_password_uc,
    get_verify_token_uc, 
)
from apps.tcc.usecase.usecases.base import password_service

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
            email = input_data.get('email', 'unknown')
            logger.info(f"Login attempt for email: {email}")
            logger.debug(f"Full input data: {input_data}")
            
            # Log context if available
            if context:
                logger.debug(f"Context: {context}")
            
            # Pass context directly, not as empty dict
            result = await self.login_uc.execute(input_data, None, context)
            
            logger.info(f"Login successful for email: {email}")
            return result
            
        except InvalidAuthInputException as e:
            # Log more details about invalid auth
            logger.warning(f"Invalid login attempt for {email}: {e.user_message}")
            logger.warning(f"Field errors: {e.field_errors if hasattr(e, 'field_errors') else 'No field errors'}")
            logger.warning(f"Exception details: {e.details if hasattr(e, 'details') else 'No details'}")
            raise  # Just re-raise without modification
            
        except AccountLockedException as e:
            logger.warning(f"Account locked for {email}: {e.user_message}")
            raise
            
        except AccountInactiveException as e:
            logger.warning(f"Account inactive for {email}: {e.user_message}")
            raise
            
        except Exception as e:
            # Log the ACTUAL exception that occurred
            logger.error(f"Unexpected login error for {email}: {str(e)}", exc_info=True)
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            
            # Wrap unexpected errors
            raise InvalidAuthInputException(
                field_errors={"general": ["Login service error"]},
                user_message="Unable to process login request. Please try again.",
                operation_id=context.get('operation_id') if isinstance(context, dict) else None
            )
        
    @BaseController.handle_exceptions
    async def logout(self, input_data: Dict[str, Any], 
                     current_user: Any, context=None) -> LogoutResponseSchema:
        """Handle user logout"""
        if not self._initialized:
            await self.initialize()
        # Pass context directly, not as empty dict
        return await self.logout_uc.execute(input_data, current_user, context)

    @BaseController.handle_exceptions
    async def refresh_token(self, input_data: Dict[str, Any], 
                           context=None) -> TokenRefreshResponseSchema:
        """Refresh access token"""
        if not self._initialized:
            await self.initialize()
        # Pass context directly, not as empty dict
        return await self.refresh_uc.execute(input_data, None, context)

    @BaseController.handle_exceptions
    async def forgot_password(self, input_data: Dict[str, Any], 
                             context=None) -> ForgotPasswordResponseSchema:
        """Handle forgot password request"""
        if not self._initialized:
            await self.initialize()
        # Pass context directly, not as empty dict
        return await self.forgot_password_uc.execute(input_data, None, context)

    @BaseController.handle_exceptions
    async def reset_password(self, input_data: Dict[str, Any], 
                            context=None) -> ResetPasswordResponseSchema:
        """Handle password reset"""
        if not self._initialized:
            await self.initialize()
        # Pass context directly, not as empty dict
        return await self.reset_password_uc.execute(input_data, None, context)

     
    @BaseController.handle_exceptions
    async def verify_token(self, input_data: Dict[str, Any], context=None) -> AuthSuccessResponseSchema:
        """Verify if token is still valid using VerifyTokenUseCase"""
        if not self._initialized:
            await self.initialize()
        
        # Pass the input data (which contains the token) to the use case
        return await self.verify_token_uc.execute(input_data, None, context)


async def create_auth_controller() -> AuthController:
    """Factory function to create and initialize AuthController"""
    controller = AuthController()
    await controller.initialize()
    return controller