from datetime import datetime, timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.schemas.out_schemas.aut_out_schemas import TokenRefreshResponseSchema, TokenResponseSchema
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema
from apps.tcc.usecase.domain_exception.auth_exceptions import AccountInactiveException, InvalidTokenException, InvalidUserInputError
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.core_exceptions.base import ErrorContext


class RefreshTokenUseCase(BaseUseCase):
    """Token refresh use case with output schema support"""

    def __init__(self, user_repository: UserRepository, jwt_provider):
        super().__init__()
        self.user_repository = user_repository
        self.jwt_provider = jwt_provider

    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, data, ctx):
        if "refresh" not in data:
            raise InvalidUserInputError(
                message="Refresh token is required",
                field_errors={"refresh": ["Refresh token is required"]}
            )

    async def _on_execute(self, data, user, ctx):
        try:
            token = RefreshToken(data["refresh"])
            user_id = token["user_id"]

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

            # Sync: Token generation
            new_tokens = self.jwt_provider.generate_tokens(user_model)
            
            # Build token data for TokenResponseSchema
            expires_in = new_tokens.get("expires_in", 3600)  # Default 1 hour
            token_data = {
                "access_token": new_tokens["access"],
                "refresh_token": new_tokens.get("refresh"),
                "token_type": "bearer",
                "expires_in": expires_in,
                "expires_at": datetime.utcnow() + timedelta(seconds=expires_in)
            }
            
            # Return TokenRefreshResponseSchema directly
            return TokenRefreshResponseSchema(
                message="Token refreshed successfully",
                tokens=TokenResponseSchema(**token_data)
            )

        except Exception as e:
            # Check if it's already one of our custom exceptions
            if isinstance(e, (InvalidTokenException, AccountInactiveException)):
                raise e
                
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