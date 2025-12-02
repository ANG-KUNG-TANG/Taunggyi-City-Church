from datetime import datetime, timedelta
from typing import Dict, Any
from apps.core.schemas.input_schemas.auth import RefreshTokenInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import TokenRefreshResponseSchema, TokenResponseSchema
from apps.tcc.usecase.domain_exception.auth_exceptions import AccountInactiveException, InvalidTokenException
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.core_exceptions.base import ErrorContext


class RefreshTokenUseCase(BaseUseCase):
    """Token refresh use case - returns TokenRefreshResponseSchema"""

    def __init__(self, user_repository: UserRepository, jwt_provider):
        super().__init__()
        self.user_repository = user_repository
        self.jwt_provider = jwt_provider

    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, data, ctx):
        """Validate input using RefreshTokenInputSchema"""
        try:
            self.validated_input = RefreshTokenInputSchema(**data)
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
        """Execute token refresh business logic - returns TokenRefreshResponseSchema"""
        refresh_token = self.validated_input.refresh_token

        try:
            # Business Rule: Validate refresh token and extract user_id
            user_id = await self._validate_refresh_token(refresh_token)
            
            # Business Rule: Verify user exists and is active
            user_model = await self.user_repository.get_by_id(user_id)
            if not user_model or not user_model.is_active:
                context = ErrorContext(
                    operation="TOKEN_REFRESH",
                    user_identifier=getattr(user_model, 'email', 'unknown'),
                    endpoint="auth/refresh"
                )
                raise AccountInactiveException(
                    username=getattr(user_model, 'email', 'unknown'),
                    user_id=user_id,
                    context=context
                )

            # Business Rule: Generate new tokens (token rotation)
            new_tokens = self.jwt_provider.generate_tokens(user_model)
            
            # Return TokenRefreshResponseSchema (domain schema)
            return self._build_refresh_response(new_tokens)

        except (AccountInactiveException, InvalidTokenException):
            raise
        except Exception as e:
            context = ErrorContext(
                operation="TOKEN_REFRESH",
                endpoint="auth/refresh"
            )
            raise InvalidTokenException(
                token_type="refresh",
                reason="Token is invalid or expired",
                context=context,
                cause=e
            )

    async def _validate_refresh_token(self, refresh_token: str) -> str:
        """Business Rule: Validate refresh token and extract user_id"""
        try:
            # Example implementation - adjust based on your JWT provider
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            return token["user_id"]
        except Exception as e:
            context = ErrorContext(operation="TOKEN_VALIDATION")
            raise InvalidTokenException(
                token_type="refresh",
                reason="Invalid or expired refresh token",
                context=context,
                cause=e
            )

    def _build_refresh_response(self, tokens: Dict[str, Any]) -> TokenRefreshResponseSchema:
        """Build TokenRefreshResponseSchema (domain schema)"""
        expires_in = tokens.get("expires_in", 3600)
        token_data = {
            "access_token": tokens.get("access"),
            "refresh_token": tokens.get("refresh"),
            "token_type": "bearer",
            "expires_in": expires_in,
            "expires_at": datetime.utcnow() + timedelta(seconds=expires_in)
        }
        
        return TokenRefreshResponseSchema(
            tokens=TokenResponseSchema(**token_data)
        )