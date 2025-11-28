from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserNotFoundException
)
from apps.core.schemas.out_schemas.base import DeleteResponseSchema

class DeleteUserUseCase(BaseUseCase):
    """Use case for soft deleting users - without builder pattern"""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        user_id = input_data.get('user_id')
        if not user_id:
            raise InvalidUserInputException(
                field_errors={"user_id": ["User ID is required"]},
                user_message="Please provide a valid user ID."
            )
        
        # Validate user_id is numeric
        try:
            int(user_id)
        except (ValueError, TypeError):
            raise InvalidUserInputException(
                field_errors={"user_id": ["User ID must be a number"]},
                user_message="Please provide a valid user ID."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> DeleteResponseSchema:
        user_id = int(input_data['user_id'])
        
        # Check if user exists before deletion
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # Soft delete user
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