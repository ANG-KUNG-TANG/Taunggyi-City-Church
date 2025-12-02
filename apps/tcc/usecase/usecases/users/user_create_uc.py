from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.auth.jwt_uc import JWTCreateUseCase
from apps.tcc.usecase.domain_exception.u_exceptions import UserAlreadyExistsException
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase


class CreateUserUseCase(BaseUseCase):
    """User creation use case with email uniqueness check and JWT generation"""
    
    def __init__(self, user_repository: UserRepository, jwt_uc: JWTCreateUseCase, **dependencies):
        super().__init__(user_repository=user_repository, jwt_uc=jwt_uc, **dependencies)
        self.user_repository = user_repository
        self.jwt_uc = jwt_uc
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Allow registration
        self.config.validate_input = True
        self.config.audit_log = True

    async def _validate_input(self, input_data, ctx):
        """Validate email uniqueness using repository business function"""
        email = input_data.get('email')
        if not email:
            raise UserAlreadyExistsException(
                email=email,
                user_message="Email is required."
            )
        
        # Use repository's email_exists business function
        if await self.user_repository.email_exists(email):
            raise UserAlreadyExistsException(
                email=email,
                user_message="An account with this email already exists."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Dict[str, Any]:
        """Execute user creation with audit context and token generation"""
        # Add audit context
        user_data = self._add_audit_context(input_data, user, ctx)
        
        # Create user using repository (handles password encryption)
        created_user = await self.user_repository.create(user_data)

        # Generate tokens using JWT use case
        tokens = await self.jwt_uc.execute(
            user_id=str(created_user.id),
            email=created_user.email,
            roles=[created_user.role] if hasattr(created_user, 'role') else ['user']
        )

        return {
            "user": UserResponseSchema.model_validate(created_user),
            "tokens": tokens,
            "message": "User created successfully"
        }