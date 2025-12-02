import asyncio
from datetime import datetime, timedelta
from django.contrib.auth import authenticate
from apps.core.schemas.input_schemas.auth import LoginInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import LoginResponseSchema, TokenResponseSchema
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema
from apps.tcc.usecase.domain_exception.auth_exceptions import AccountInactiveException, InvalidCredentialsException
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.core_exceptions.base import ErrorContext


class LoginUseCase(BaseUseCase):
    """User login use case - returns LoginResponseSchema (domain schema)"""

    def __init__(self, jwt_provider, auth_service: AsyncAuthDomainService):
        super().__init__()
        self.jwt_provider = jwt_provider
        self.auth_service = auth_service
    
    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.required_roles = []

    async def _validate_input(self, data, ctx):
        """Validate input using LoginInputSchema"""
        try:
            # Validate against schema
            self.validated_input = LoginInputSchema(**data)
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
        """Execute login business logic - returns LoginResponseSchema"""
        email = self.validated_input.email
        password = self.validated_input.password
        remember_me = self.validated_input.remember_me

        # Business Rule: Credential verification
        user_model = authenticate(username=email, password=password)

        if not user_model:
            context = ErrorContext(
                operation="LOGIN",
                user_identifier=email,
                endpoint="auth/login"
            )
            raise InvalidCredentialsException(
                username=email,
                reason="Invalid email or password",
                context=context
            )

        # Business Rule: Check if user is active
        if not user_model.is_active:
            context = ErrorContext(
                operation="LOGIN",
                user_identifier=email,
                endpoint="auth/login"
            )
            raise AccountInactiveException(
                username=email,
                user_id=user_model.id,
                context=context
            )

        # Business Rule: Generate tokens
        tokens = self.jwt_provider.generate_tokens(user_model)
        
        # Apply remember_me business rule for refresh token expiry
        if remember_me:
            tokens = self._apply_remember_me_rules(tokens)

        # Business Rule: Audit logging (async fire-and-forget)
        request_meta = ctx.get('request_meta', {}) if ctx else {}
        asyncio.create_task(
            self.auth_service.audit_login_async(user_model.id, "LOGIN", request_meta)
        )
        
        # Return LoginResponseSchema (domain schema)
        return self._build_login_response(user_model, tokens)

    def _apply_remember_me_rules(self, tokens: dict) -> dict:
        """Apply remember_me business rules to tokens"""
        # Implementation depends on your JWT provider
        # For now, return the same tokens
        return tokens

    def _build_login_response(self, user_model, tokens: dict) -> LoginResponseSchema:
        """Build LoginResponseSchema (domain schema)"""
        # Build user data for UserResponseSchema
        user_data = {
            "id": user_model.id,
            "email": user_model.email,
            "name": getattr(user_model, 'name', ''),
            "role": getattr(user_model, 'role', 'user'),
            "is_active": user_model.is_active,
            "created_at": getattr(user_model, 'created_at', None),
            "updated_at": getattr(user_model, 'updated_at', None)
        }
        
        # Build token data for TokenResponseSchema
        expires_in = tokens.get("expires_in", 3600)
        token_data = {
            "access_token": tokens.get("access"),
            "refresh_token": tokens.get("refresh"),
            "token_type": "bearer",
            "expires_in": expires_in,
            "expires_at": datetime.utcnow() + timedelta(seconds=expires_in)
        }
        
        # Return LoginResponseSchema
        return LoginResponseSchema(
            message="Login successful",
            user=UserResponseSchema(**user_data),
            tokens=TokenResponseSchema(**token_data),
            requires_2fa=getattr(user_model, 'requires_2fa', False)
        )