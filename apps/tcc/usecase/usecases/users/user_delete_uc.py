from typing import Dict, Any
from usecases.base.base_uc  import OperationPortalUseCase
from usecase.exceptions.u_exceptions import (
    InvalidUserInputError,
    UserNotFoundException
)

class DeleteUserUseCase(OperationPortalUseCase):
    """Use case for soft deleting users"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    def _validate_input(self, input_data: Dict[str, Any], context):
        user_id = input_data.get('user_id')
        if not user_id:
            raise InvalidUserInputError(details={
                "message": "User ID is required",
                "field": "user_id"
            })

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        user_id = input_data['user_id']
        
        # Check if user exists before deletion
        existing_user = self.user_repository.get_by_id(user_id, user)
        if not existing_user:
            raise UserNotFoundException(user_id=user_id)
        
        # Soft delete user
        success = self.user_repository.delete(user_id, user)
        
        if not success:
            raise UserNotFoundException(user_id=user_id)
        
        return {
            "message": "User deleted successfully",
            "user_id": user_id
        }