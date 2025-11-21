import asyncio
from django.contrib.auth import authenticate
from apps.core.helpers.jwt_helper import JWTProvider
from apps.core.security.dtos import AuthResponseDTO
from apps.tcc.usecase.services.auth.asyn_auth_servic import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.u_exceptions import InvalidUserInputError, UserAuthenticationError

class LoginUseCase(BaseUseCase):

    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.required_roles = []

    def _validate_input(self, data, ctx):
        if not data.get("email") or not data.get("password"):
            raise InvalidUserInputError(message="Email and password required")

    async def _on_execute(self, data, user, ctx):
        # Sync: Credential verification
        user_model = authenticate(username=data["email"], password=data["password"])

        if not user_model:
            raise UserAuthenticationError(message="Invalid credentials")

        # Sync: Token generation
        tokens = JWTProvider.generate_tokens(user_model)

        # Async: Audit logging (fire-and-forget)
        asyncio.create_task(
            AsyncAuthDomainService().audit_login_async(user_model.id, "LOGIN")
        )

        return AuthResponseDTO.from_user(user_model, tokens)