from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.helpers.jwt_helper import JWTProvider
from apps.core.security.dtos import TokenRefreshResponseDTO
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.u_exceptions import InvalidUserInputError, UserAuthenticationError


class RefreshTokenUseCase(BaseUseCase):

    def _setup_configuration(self):
        self.config.require_authentication = False

    def _validate_input(self, data, ctx):
        if "refresh" not in data:
            raise InvalidUserInputError("Refresh token is required")

    def _on_execute(self, data, user, ctx):
        try:
            token = RefreshToken(data["refresh"])
            user_id = token["user_id"]

            user_model = self.user_repository.get_by_id(user_id)
            if not user_model.is_active:
                raise UserAuthenticationError("User inactive")

            # Sync: Token generation
            new_tokens = JWTProvider.generate_tokens(user_model)
            return TokenRefreshResponseDTO(**new_tokens)

        except Exception:
            raise UserAuthenticationError("Invalid refresh token")