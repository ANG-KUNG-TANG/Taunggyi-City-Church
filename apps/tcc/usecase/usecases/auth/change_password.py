import asyncio
from datetime import datetime
from typing import Dict, Any
from pydantic import ValidationError

from apps.core.schemas.input_schemas.auth import ChangePasswordInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import ChangePasswordResponseSchema
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.password_service import PasswordService
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
import logging

logger = logging.getLogger(__name__)


class ChangePasswordUseCase(BaseUseCase):
    """Change user password (requires current password)"""

    def __init__(self, user_repository: UserRepository,
                 password_service: PasswordService,
                 auth_service: AsyncAuthDomainService):
        super().__init__()
        self.user_repository = user_repository
        self.password_service = password_service
        self.auth_service = auth_service

    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.audit_log = True

    async def _validate_input(self, data, ctx):
        """Validate change password input"""
        if not data or not isinstance(data, dict):
            raise InvalidUserInputException(
                field_errors={"general": ["Password change data is required"]},
                user_message="Please provide all required fields."
            )
        
        # Check for missing fields
        missing_fields = []
        for field in ['current_password', 'new_password', 'confirm_password']:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            field_errors = {}
            for field in missing_fields:
                field_errors[field] = [f"{field.replace('_', ' ').title()} is required"]
            
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message=f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # Validate with Pydantic
        try:
            self.validated_input = ChangePasswordInputSchema(**data)
        except ValidationError as e:
            field_errors = {}
            for error in e.errors():
                field = error['loc'][0] if error['loc'] else 'general'
                msg = error['msg']
                
                if error.get('type') == 'value_error.missing':
                    msg = f"{field.replace('_', ' ').title()} is required"
                
                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(msg)
            
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message="Please check your password input."
            )

    async def _on_execute(self, data, user, ctx):
        """Execute password change"""
        current_password = self.validated_input.current_password
        new_password = self.validated_input.new_password
        request_meta = ctx.get('request_meta', {}) if ctx else {}
        
        # 1. Verify current password
        password_valid = await self.password_service.verify_password(
            current_password,
            user.password_hash
        )
        
        if not password_valid:
            raise InvalidUserInputException(
                field_errors={"current_password": ["Current password is incorrect"]},
                user_message="Current password is incorrect."
            )
        
        # 2. Check password strength
        is_strong, strength_message = self.password_service.is_password_strong(new_password)
        if not is_strong:
            raise InvalidUserInputException(
                field_errors={"new_password": [strength_message]},
                user_message=f"Password is too weak: {strength_message}"
            )
        
        # 3. Check password history
        password_history = getattr(user, 'password_history', [])
        for old_hash in password_history[-5:]:
            if await self.password_service.verify_password(new_password, old_hash):
                raise InvalidUserInputException(
                    field_errors={"new_password": ["Cannot reuse previous passwords"]},
                    user_message="You cannot reuse a previous password."
                )
        
        # 4. Hash and update password
        hashed_password = await self.password_service.hash_password(new_password)
        
        # Update password in database
        await self.user_repository.update(user.id, {
            'password_hash': hashed_password,
            'last_password_change': datetime.utcnow(),
            'requires_password_change': False
        })
        
        # 5. Audit logging
        asyncio.create_task(
            self.auth_service.audit_login_async(
                user.id,
                "PASSWORD_CHANGED",
                request_meta
            )
        )
        
        return ChangePasswordResponseSchema(
            message="Password changed successfully",
            success=True
        )