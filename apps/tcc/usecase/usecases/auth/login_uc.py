import asyncio
from django.contrib.auth import authenticate
from apps.core.schemas.builders.builder import UserResponseBuilder
from apps.core.schemas.common.response import LoginResponse, make_login_response
from apps.tcc.usecase.domain_exception.auth_exceptions import AccountInactiveException, InvalidCredentialsException, InvalidUserInputError
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.core_exceptions.base import ErrorContext


class LoginUseCase(BaseUseCase):
    """User login use case"""

    def __init__(self, jwt_provider, auth_service: AsyncAuthDomainService):
        super().__init__()
        self.jwt_provider = jwt_provider
        self.auth_service = auth_service
    
    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.required_roles = []

    async def _validate_input(self, data, ctx):
        if not data.get("email") or not data.get("password"):
            raise InvalidUserInputError(
                message="Email and password required",
                field_errors={
                    "email": ["Email is required"],
                    "password": ["Password is required"]
                }
            )

    async def _on_execute(self, data, user, ctx):
        # Sync: Credential verification
        user_model = authenticate(username=data["email"], password=data["password"])

        if not user_model:
            context = ErrorContext(
                operation="LOGIN",
                user_identifier=data["email"],
                endpoint="auth/login"
            )
            raise InvalidCredentialsException(
                username=data["email"],
                reason="Invalid email or password",
                context=context
            )

        # Check if user is active
        if not user_model.is_active:
            context = ErrorContext(
                operation="LOGIN",
                user_identifier=data["email"],
                endpoint="auth/login"
            )
            raise AccountInactiveException(
                username=data["email"],
                user_id=user_model.id,
                context=context
            )

        # Sync: Token generation
        tokens = self.jwt_provider.generate_tokens(user_model)

        # Async: Audit logging (fire-and-forget)
        asyncio.create_task(
            self.auth_service.audit_login_async(user_model.id, "LOGIN")
        )
        
        # Build response using make_login_response helper
        user_response = UserResponseBuilder.to_response(user_model)
        return make_login_response(
            access_token=tokens["access"],
            refresh_token=tokens.get("refresh"),
            expires_in=tokens.get("expires_in"),
            user=user_response.model_dump(),
            message="Login successful"
        )