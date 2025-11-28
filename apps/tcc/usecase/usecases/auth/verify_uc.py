from apps.core.schemas.out_schemas.aut_out_schemas import AuthSuccessResponseSchema
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase


class VerifyTokenUseCase(BaseUseCase):
    """Token verification use case with output schema support"""

    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, data, user, ctx):
        # Build user data for UserResponseSchema
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at if hasattr(user, 'created_at') else None,
            "updated_at": user.updated_at if hasattr(user, 'updated_at') else None
        }
        
        # Return AuthSuccessResponseSchema directly
        return AuthSuccessResponseSchema(
            message="Token is valid",
            user=UserResponseSchema(**user_data),
            tokens=None  # No new tokens in verify endpoint
        )