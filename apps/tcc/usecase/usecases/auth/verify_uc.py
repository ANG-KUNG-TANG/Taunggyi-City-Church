from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase


class VerifyTokenUseCase(BaseUseCase):
    """Token verification use case"""

    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, data, user, ctx):
        user_data = {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "permissions": user.get_permissions(),
            "active": user.is_active
        }
        
        return APIResponse.success_response(
            message="Token is valid",
            data=user_data
        )