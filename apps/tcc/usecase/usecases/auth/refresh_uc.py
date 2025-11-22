from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.schemas.builders.builder import UserResponseBuilder
from apps.core.schemas.common.response import LoginResponse, make_login_response
from apps.tcc.usecase.domain_exception.auth_exceptions import AccountInactiveException, InvalidTokenException, InvalidUserInputError
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.core_exceptions.base import ErrorContext


class RefreshTokenUseCase(BaseUseCase):
    """Token refresh use case"""

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
            if not user_model.is_active:
                context = ErrorContext(
                    operation="TOKEN_REFRESH",
                    user_identifier=user_model.email,
                    endpoint="auth/refresh"
                )
                raise AccountInactiveException(
                    username=user_model.email,
                    user_id=user_id,
                    context=context
                )

            # Sync: Token generation
            new_tokens = self.jwt_provider.generate_tokens(user_model)
            
            # Build user response
            user_response = UserResponseBuilder.to_response(user_model)
            
            # Use the same login response structure for consistency
            return make_login_response(
                access_token=new_tokens["access"],
                refresh_token=new_tokens.get("refresh"),
                expires_in=new_tokens.get("expires_in"),
                user=user_response.model_dump(),
                message="Token refreshed successfully"
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