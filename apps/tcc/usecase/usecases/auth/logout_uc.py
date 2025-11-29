import asyncio
from apps.core.schemas.input_schemas.auth import LogoutInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import LogoutResponseSchema
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase


class LogoutUseCase(BaseUseCase):
    """User logout use case with proper schema usage"""

    def __init__(self, auth_service: AsyncAuthDomainService):
        super().__init__()
        self.auth_service = auth_service

    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, data, ctx):
        """Validate input using LogoutInputSchema"""
        try:
            self.validated_input = LogoutInputSchema(**data)
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
        """Execute logout business logic"""
        token_str = self.validated_input.refresh_token
        
        # Business Rule: Token revocation (if provided) - fire and forget
        if token_str:
            asyncio.create_task(
                self.auth_service.revoke_token_async(token_str, user.id)
            )
        
        # Business Rule: Audit logging with context - fire and forget
        request_meta = ctx.get('request_meta', {}) if ctx else {}
        asyncio.create_task(
            self.auth_service.audit_login_async(user.id, "LOGOUT", request_meta)
        )

        # Return response using output schema
        return LogoutResponseSchema(message="Logout successful")