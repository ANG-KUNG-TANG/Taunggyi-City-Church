from typing import Dict, Any
from apps.core.schemas.out_schemas.base import StatusResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.u_exceptions import UserAlreadyExistsException
from apps.tcc.usecase.entities.users import UserEntity
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.auth.jwt_uc import JWTCreateUseCase


class CreateUserUseCase(BaseUseCase):
    """User creation use case - assumes data is pre-validated by decorators"""
    
    def __init__(self, user_repository: UserRepository, jwt_uc: JWTCreateUseCase):
        super().__init__()
        self.user_repository = user_repository
        self.jwt_uc = jwt_uc
    
    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.required_permissions = []

    async def _validate_input(self, input_data: Dict[str, Any], context):
        # Only check business rules (email uniqueness)
        # Input data is already validated by decorator
        if await self.user_repository.email_exists(input_data['email']):
            raise UserAlreadyExistsException(
                email=input_data['email'],
                user_message="An account with this email already exists."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        # Add audit context to input data
        input_data_with_context = input_data.copy()
        if context and hasattr(context, 'request'):
            request = context.request
            input_data_with_context['ip_address'] = self._get_client_ip(request)
            input_data_with_context['user_agent'] = request.META.get('HTTP_USER_AGENT', 'system')
        
        # Create user using repository with the prepared data
        created_user = await self.user_repository.create(input_data_with_context)

        # Generate tokens
        tokens = await self.jwt_uc.execute(
            user_id=str(created_user.id),
            email=created_user.email,
            roles=[created_user.role]
        )

        # Return raw data for response building
        return {
            "user": created_user,
            "tokens": tokens,
            "message": "User created successfully"
        }
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip