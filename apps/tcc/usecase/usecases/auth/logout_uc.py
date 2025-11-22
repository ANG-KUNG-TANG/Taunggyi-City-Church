import asyncio
from apps.core.schemas.common.response import LogoutResponse, make_logout_response
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.core_exceptions.base import ErrorContext


class LogoutUseCase(BaseUseCase):
    """User logout use case"""

    def __init__(self, auth_service: AsyncAuthDomainService):
        super().__init__()
        self.auth_service = auth_service

    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, data, user, ctx):
        token_str = data.get("refresh")
        
        # Async: Token revocation (if provided)
        if token_str:
            asyncio.create_task(
                self.auth_service.revoke_token_async(token_str)
            )
        
        # Async: Audit logging
        asyncio.create_task(
            self.auth_service.audit_login_async(user.id, "LOGOUT")
        )

        return make_logout_response(message="Logout successful")