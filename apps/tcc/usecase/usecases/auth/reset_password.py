import asyncio
from apps.core.schemas.input_schemas.auth import ResetPasswordInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import ResetPasswordResponseSchema
from apps.tcc.usecase.domain_exception.auth_exceptions import InvalidResetTokenException
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.core_exceptions.base import ErrorContext


class ResetPasswordUseCase(BaseUseCase):
    """Reset password use case - returns ResetPasswordResponseSchema"""

    def __init__(self, user_repository: UserRepository, auth_service: AsyncAuthDomainService):
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service
    
    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, data, ctx):
        """Validate input using ResetPasswordInputSchema"""
        try:
            self.validated_input = ResetPasswordInputSchema(**data)
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
        """Execute reset password business logic - returns ResetPasswordResponseSchema"""
        reset_token = self.validated_input.reset_token
        new_password = self.validated_input.new_password
        
        # Business Rule: Validate reset token
        token_data = await self.auth_service.validate_password_reset_token(reset_token)
        if not token_data:
            context = ErrorContext(
                operation="RESET_PASSWORD",
                endpoint="auth/reset-password"
            )
            raise InvalidResetTokenException(
                token=reset_token,
                reason="Invalid or expired reset token",
                context=context
            )
        
        user_id = token_data.get('user_id')
        
        # Business Rule: Get user
        user_model = await self.user_repository.get_by_id(user_id)
        if not user_model:
            context = ErrorContext(
                operation="RESET_PASSWORD",
                user_identifier=user_id,
                endpoint="auth/reset-password"
            )
            raise InvalidResetTokenException(
                token=reset_token,
                reason="User not found",
                context=context
            )
        
        # Business Rule: Update password
        await self.auth_service.update_user_password_async(
            user_id=str(user_model.id),
            new_password=new_password
        )
        
        # Business Rule: Invalidate all existing sessions (async)
        asyncio.create_task(
            self.auth_service.invalidate_user_sessions_async(str(user_model.id))
        )
        
        # Business Rule: Revoke the reset token (async)
        asyncio.create_task(
            self.auth_service.revoke_reset_token_async(reset_token)
        )
        
        # Return ResetPasswordResponseSchema (domain schema)
        return ResetPasswordResponseSchema(
            message="Password reset successful. Please login with your new password.",
            reset_successful=True
        )