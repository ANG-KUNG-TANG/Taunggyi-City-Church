from apps.core.schemas.out_schemas.aut_out_schemas import AuthSuccessResponseSchema
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase

class VerifyTokenUseCase(BaseUseCase):
    """Token verification use case with proper schema usage"""

    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, data, user, ctx):
        """Execute token verification business logic"""
        # Business Rule: Token is already validated by authentication middleware
        # This use case just returns user information
        
        # Build user data for UserResponseSchema
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": getattr(user, 'name', ''),
            "role": getattr(user, 'role', 'user'),
            "is_active": user.is_active,
            "created_at": getattr(user, 'created_at', None),
            "updated_at": getattr(user, 'updated_at', None)
        }
        
        # Return response using output schema
        return AuthSuccessResponseSchema(
            message="Token is valid",
            user=UserResponseSchema(**user_data),
            tokens=None  
        )