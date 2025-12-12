from datetime import datetime
from typing import Dict, Any
from pydantic import ValidationError

from apps.core.schemas.input_schemas.auth import ResetPasswordInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import ResetPasswordResponseSchema
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.password_service import PasswordService
import logging

logger = logging.getLogger(__name__)


class ResetPasswordUseCase(BaseUseCase):
    """Reset password using reset token"""

    def __init__(self, user_repository: UserRepository,
                 auth_service: AsyncAuthDomainService,
                 password_service: PasswordService):
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.password_service = password_service

    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.transactional = True

    async def _validate_input(self, data, ctx):
        """Validate reset password input"""
        # Check if we have the basic data structure
        if not data or not isinstance(data, dict):
            raise InvalidUserInputException(
                field_errors={"general": ["Reset data is required"]},
                user_message="Please provide all required fields."
            )
        
        # Check for missing required fields
        missing_fields = []
        if not data.get('token'):
            missing_fields.append('token')
        if not data.get('new_password'):
            missing_fields.append('new_password')
        if not data.get('confirm_password'):
            missing_fields.append('confirm_password')
        
        if missing_fields:
            field_errors = {}
            for field in missing_fields:
                field_errors[field] = [f"{field.replace('_', ' ').title()} is required"]
            
            user_message = f"Missing required fields: {', '.join(missing_fields)}"
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message=user_message
            )
        
        # Now validate with Pydantic schema
        try:
            self.validated_input = ResetPasswordInputSchema(**data)
        except ValidationError as e:
            # Format Pydantic errors
            field_errors = {}
            for error in e.errors():
                field = error['loc'][0] if error['loc'] else 'general'
                msg = error['msg']
                
                # Customize error messages
                error_type = error.get('type', '')
                if error_type == 'value_error.missing':
                    msg = f"{field.replace('_', ' ').title()} is required"
                elif 'min_length' in error_type:
                    msg = f"Must be at least {error.get('ctx', {}).get('limit_value', 8)} characters"
                
                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(msg)
            
            # Determine user-friendly message
            user_message = "Please check your input and try again."
            if 'new_password' in field_errors and 'confirm_password' in field_errors:
                user_message = "Password and confirmation are required"
            elif 'token' in field_errors:
                user_message = "Reset token is required"
            
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message=user_message
            )

    async def _on_execute(self, data, user, ctx):
        """Process password reset"""
        # FIXED: Use 'token' instead of 'reset_token' to match schema
        reset_token = self.validated_input.token
        new_password = self.validated_input.new_password
        request_meta = ctx.get('request_meta', {}) if ctx else {}
        
        # 1. Validate reset token
        token_valid, token_data = await self.auth_service.validate_reset_token(reset_token)
        
        if not token_valid:
            raise InvalidUserInputException(
                field_errors={"token": ["Invalid or expired reset token"]},
                user_message="The reset link is invalid or has expired."
            )
        
        user_id = token_data['user_id']
        
        # 2. Get user
        user_entity = await self.user_repository.get_by_id(user_id)
        if not user_entity:
            raise InvalidUserInputException(
                field_errors={"user": ["User not found"]},
                user_message="User account not found."
            )
        
        # 3. Check password strength
        is_strong, strength_message = self.password_service.is_password_strong(new_password)
        if not is_strong:
            raise InvalidUserInputException(
                field_errors={"new_password": [strength_message]},
                user_message=f"Password is too weak: {strength_message}"
            )
        
        # 4. Check password history (optional - prevent reuse)
        password_history = getattr(user_entity, 'password_history', [])
        for old_hash in password_history[-5:]:  # Check last 5 passwords
            if await self.password_service.verify_password(new_password, old_hash):
                raise InvalidUserInputException(
                    field_errors={"new_password": ["Cannot reuse previous passwords"]},
                    user_message="You cannot reuse a previous password."
                )
        
        # 5. Hash new password
        hashed_password = await self.password_service.hash_password(new_password)
        
        # 6. Update user
        await self.user_repository.update(user_id, {
            'password_hash': hashed_password,
            'last_password_change': datetime.utcnow(),
            'failed_login_attempts': 0,  # Reset on password change
            'is_locked': False,
            'lock_reason': None,
            'requires_password_change': False
        })
        
        # 7. Invalidate reset token
        await self.auth_service.invalidate_reset_token(reset_token)
        
        # 8. Invalidate all sessions (optional - for security)
        await self.auth_service.invalidate_all_sessions_async(user_id)
        
        # 9. Send notification (async)
        await self.auth_service.send_password_changed_notification_async(
            user_id=user_id,
            email=user_entity.email,
            request_meta=request_meta
        )
        
        # 10. Audit log
        await self.auth_service.audit_login_async(
            user_id, 
            "PASSWORD_RESET",
            request_meta
        )
        
        return ResetPasswordResponseSchema(
            message="Password reset successfully",
            user_id=user_id,
            success=True,
            requires_login=True
        )