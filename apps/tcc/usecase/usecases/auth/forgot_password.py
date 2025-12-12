import asyncio
from typing import Dict, Any
from pydantic import ValidationError

from apps.core.schemas.input_schemas.auth import ForgotPasswordInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import ForgotPasswordResponseSchema
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
import logging

logger = logging.getLogger(__name__)


class ForgotPasswordUseCase(BaseUseCase):
    """Handle password reset requests"""

    def __init__(self, user_repository: UserRepository, 
                 auth_service: AsyncAuthDomainService):
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service

    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, data, ctx):
        """Validate forgot password input"""
        # Check if we have the basic data structure
        if not data or not isinstance(data, dict):
            raise InvalidUserInputException(
                field_errors={"general": ["Email is required"]},
                user_message="Please provide your email address."
            )
        
        # Check for missing email
        email = data.get('email', '').strip()
        if not email:
            raise InvalidUserInputException(
                field_errors={"email": ["Email is required"]},
                user_message="Please provide your email address."
            )
        
        # Now validate with Pydantic schema for email format
        try:
            self.validated_input = ForgotPasswordInputSchema(**data)
        except ValidationError as e:
            # Format Pydantic errors
            field_errors = {}
            for error in e.errors():
                field = error['loc'][0] if error['loc'] else 'general'
                msg = error['msg']
                
                # Customize error messages
                error_type = error.get('type', '')
                if error_type == 'value_error.missing':
                    msg = "Email is required"
                elif error_type == 'value_error.email':
                    msg = "Please enter a valid email address"
                
                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(msg)
            
            user_message = "Please provide a valid email address."
            if 'email' in field_errors:
                user_message = field_errors['email'][0]
            
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message=user_message
            )

    async def _on_execute(self, data, user, ctx):
        """Process password reset request"""
        email = self.validated_input.email.lower().strip()
        
        # 1. Check rate limiting (prevent email bombing)
        can_proceed = await self.auth_service.check_rate_limit(
            f"forgot_password:{email}",
            max_attempts=3,
            window_minutes=15
        )
        
        if not can_proceed:
            # Return success even if rate limited (security by obscurity)
            return ForgotPasswordResponseSchema(
                message="If your email exists in our system, you will receive reset instructions.",
                email=email,
                success=True
            )
        
        # 2. Get user by email
        user_entity = await self.user_repository.get_by_email(email)
        
        if not user_entity:
            # Security: Don't reveal if user exists
            logger.info(f"Password reset requested for non-existent email: {email}")
            return ForgotPasswordResponseSchema(
                message="If your email exists in our system, you will receive reset instructions.",
                email=email,
                success=True
            )
        
        # 3. Check account status
        if getattr(user_entity, 'is_locked', False):
            # Still return success (security by obscurity)
            logger.warning(f"Password reset requested for locked account: {email}")
            return ForgotPasswordResponseSchema(
                message="If your email exists in our system, you will receive reset instructions.",
                email=email,
                success=True
            )
        
        if not getattr(user_entity, 'is_active', True):
            logger.warning(f"Password reset requested for inactive account: {email}")
            return ForgotPasswordResponseSchema(
                message="If your email exists in our system, you will receive reset instructions.",
                email=email,
                success=True
            )
        
        # 4. Generate reset token (async)
        request_meta = ctx.get('request_meta', {}) if ctx else {}
        
        asyncio.create_task(
            self.auth_service.send_password_reset_email_async(
                user_id=user_entity.id,
                email=email,
                request_meta=request_meta
            )
        )
        
        # 5. Audit log (async)
        asyncio.create_task(
            self.auth_service.audit_login_async(
                user_entity.id, 
                "FORGOT_PASSWORD_REQUEST",
                request_meta
            )
        )
        
        return ForgotPasswordResponseSchema(
            message="If your email exists in our system, you will receive reset instructions.",
            email=email,
            success=True
        )
        
