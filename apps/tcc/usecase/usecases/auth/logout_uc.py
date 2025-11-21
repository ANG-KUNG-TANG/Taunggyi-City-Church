import asyncio
from apps.core.security.dtos import LogoutResponseDTO
from apps.tcc.usecase.services.auth.asyn_auth_servic import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase

class LogoutUseCase(BaseUseCase):

    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, data, user, ctx):
        token_str = data.get("refresh")
        
        # Async: Token revocation (if provided)
        if token_str:
            asyncio.create_task(
                AsyncAuthDomainService().revoke_token_async(token_str)
            )
        
        # Async: Audit logging
        asyncio.create_task(
            AsyncAuthDomainService().audit_login_async(user.id, "LOGOUT")
        )

        return LogoutResponseDTO()