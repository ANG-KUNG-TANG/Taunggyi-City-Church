from rest_framework_simplejwt.tokens import RefreshToken

from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase

class LogoutUseCase(BaseUseCase):

    def _setup_configuration(self):
        self.config.require_authentication = True

    def _on_execute(self, data, user, ctx):
        token_str = data.get("refresh")

        if token_str:
            try:
                RefreshToken(token_str).blacklist()
            except Exception:
                pass

        return {"message": "Logged out"}
