import asyncio
import secrets
from datetime import datetime, timedelta
from apps.core.schemas.input_schemas.auth import ForgotPasswordInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import ForgotPasswordResponseSchema
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.core_exceptions.base import ErrorContext


class ForgotPasswordUseCase(BaseUseCase):
    """Forgot password use case - returns ForgotPasswordResponseSchema"""

    def __init__(self, user_repository: UserRepository, auth_service: AsyncAuthDomainService, email_service):
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.email_service = email_service
    
    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, data, ctx):
        """Validate input using ForgotPasswordInputSchema"""
        try:
            self.validated_input = ForgotPasswordInputSchema(**data)
        except Exception as e:
            field_errors = {}
            if hasattr(e, 'errors'):
                for error in e.errors():
                    field = error['loc'][0] if error['loc'] else 'general'
                    message = error['msg']
                    if field not in field_errors:
                        field_errors[field] = []
                    field_errors[field].append(message)
            else:
                field_errors['general'] = [str(e)]
            
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message="Please check your input and try again."
            )

    async def _on_execute(self, data, user, ctx):
        """Execute forgot password business logic - returns ForgotPasswordResponseSchema"""
        email = self.validated_input.email
        
        # Business Rule: Check if user exists
        user_model = await self.user_repository.get_by_email(email)
        
        if user_model:
            # Business Rule: Generate reset token
            reset_token = secrets.token_urlsafe(32)
            token_expiry = datetime.utcnow() + timedelta(hours=24)
            
            # Business Rule: Save reset token to user
            await self.auth_service.save_password_reset_token_async(
                user_id=str(user_model.id),
                reset_token=reset_token,
                expires_at=token_expiry
            )
            
            # Business Rule: Send reset email (async)
            request_meta = ctx.get('request_meta', {}) if ctx else {}
            asyncio.create_task(
                self._send_reset_email_async(user_model.email, reset_token, request_meta)
            )
        
        # Return ForgotPasswordResponseSchema (domain schema)
        return ForgotPasswordResponseSchema(
            message="If your email is registered, you will receive reset instructions shortly.",
            check_your_email=True
        )