
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase


class VerifyTokenUseCase(BaseUseCase):

    def _setup_configuration(self):
        self.config.require_authentication = True

    def _on_execute(self, data, user, ctx):
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "permissions": user.get_permissions(),
            "active": user.is_active
        }
