import asyncio
from datetime import datetime, timedelta
from django.contrib.auth import authenticate
from apps.core.schemas.out_schemas.aut_out_schemas import LoginResponseSchema, TokenResponseSchema
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema
from apps.tcc.usecase.domain_exception.auth_exceptions import AccountInactiveException, InvalidCredentialsException, InvalidUserInputError
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.core_exceptions.base import ErrorContext


class LoginUseCase(BaseUseCase):
    """User login use case with output schema support"""

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

        # Async: Audit logging with context
        request_meta = ctx.get('request_meta', {}) if ctx else {}
        asyncio.create_task(
            self.auth_service.audit_login_async(user_model.id, "LOGIN", request_meta)
        )
        
        # Build user data for UserResponseSchema
        user_data = {
            "id": user_model.id,
            "email": user_model.email,
            "name": user_model.name,
            "role": user_model.role,
            "is_active": user_model.is_active,
            "created_at": user_model.created_at,
            "updated_at": user_model.updated_at
        }
        
        # Build token data for TokenResponseSchema
        expires_in = tokens.get("expires_in", 3600)  # Default 1 hour
        token_data = {
            "access_token": tokens["access"],
            "refresh_token": tokens.get("refresh"),
            "token_type": "bearer",
            "expires_in": expires_in,
            "expires_at": datetime.utcnow() + timedelta(seconds=expires_in)
        }
        
        # Return LoginResponseSchema directly
        return LoginResponseSchema(
            message="Login successful",
            user=UserResponseSchema(**user_data),
            tokens=TokenResponseSchema(**token_data),
            requires_2fa=False  # Set based on your 2FA logic
        )