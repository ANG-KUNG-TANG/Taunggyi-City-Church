from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import UserNotFoundException
from apps.core.schemas.out_schemas.base import DeleteResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase


class DeleteUserUseCase(BaseUseCase):
    """Soft delete user using repository's delete with cache invalidation"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']
        self.config.validate_input = True
        self.config.audit_log = True

    async def _validate_input(self, input_data, ctx):
        user_id = input_data.get('user_id')
        if not user_id:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User ID is required."
            )
        
        try:
            int(user_id)
        except (ValueError, TypeError):
            raise UserNotFoundException(
                user_id=user_id,
                user_message="Invalid user ID format."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> DeleteResponseSchema:
        user_id = int(input_data['user_id'])
        
        # Check if user exists using repository
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # Soft delete using repository (includes cache invalidation)
        success = await self.user_repository.delete(user_id)
        
        if not success:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="Failed to delete user."
            )
        
        return DeleteResponseSchema(
            id=user_id,
            deleted=success,
            message="User deleted successfully"
        )