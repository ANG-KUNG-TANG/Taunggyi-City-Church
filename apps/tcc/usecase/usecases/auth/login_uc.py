from django.contrib.auth import authenticate
from apps.core.helpers.jwt_helper import JWTProvider
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.u_exceptions import InvalidUserInputError, UserAuthenticationError

class LoginUseCase(BaseUseCase):

    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.required_roles = []

    def _validate_input(self, data, ctx):
        if not data.get("email") or not data.get("password"):
            raise InvalidUserInputError(message="Email and password required")

    def _on_execute(self, data, user, ctx):
        user_model = authenticate(username=data["email"], password=data["password"])

        if not user_model:
            raise UserAuthenticationError(message="Invalid credentials")

        tokens = JWTProvider.generate_tokens(user_model)

        return {
            "tokens": tokens,
            "user": {
                "id": user_model.id,
                "email": user_model.email,
                "role": user_model.role
            }
        }
