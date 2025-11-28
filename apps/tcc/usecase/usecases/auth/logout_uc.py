import asyncio
from apps.core.schemas.out_schemas.aut_out_schemas import LogoutResponseSchema
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase


class LogoutUseCase(BaseUseCase):
    """User logout use case with output schema support"""

    def __init__(self, auth_service: AsyncAuthDomainService):
        super().__init__()
        self.auth_service = auth_service

    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, data, user, ctx):
        token_str = data.get("refresh_token")
        
        # Async: Token revocation (if provided)
        if token_str:
            asyncio.create_task(
                self.auth_service.revoke_token_async(token_str, user.id)
            )
        
        # Async: Audit logging with context
        request_meta = ctx.get('request_meta', {}) if ctx else {}
        asyncio.create_task(
            self.auth_service.audit_login_async(user.id, "LOGOUT", request_meta)
        )

        # Return LogoutResponseSchema directly
        return LogoutResponseSchema(message="Logout successful")