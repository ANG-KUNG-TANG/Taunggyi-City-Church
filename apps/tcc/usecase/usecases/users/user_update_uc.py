from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import UserNotFoundException
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase


class UpdateUserUseCase(BaseUseCase):
    """Update user using repository's update with caching invalidation"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
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

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserResponseSchema:
        user_id = int(input_data['user_id'])
        update_data = input_data.get('update_data', {})
        
        # Check if user exists using repository
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # Add audit context and update using repository (includes cache invalidation)
        update_data_with_context = self._add_audit_context(update_data, user, ctx)
        updated_user = await self.user_repository.update(user_id, update_data_with_context)
        
        if not updated_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="Failed to update user."
            )
        
        return UserResponseSchema.model_validate(updated_user)


class ChangeUserStatusUseCase(BaseUseCase):
    """Change user status using repository's update with audit context"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True
        self.config.audit_log = True

    async def _validate_input(self, input_data, ctx):
        user_id = input_data.get('user_id')
        if not user_id:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User ID is required."
            )
        
        status = input_data.get('status')
        if not status:
            raise UserNotFoundException(
                user_message="Status is required."
            )
        
        try:
            int(user_id)
        except (ValueError, TypeError):
            raise UserNotFoundException(
                user_id=user_id,
                user_message="Invalid user ID format."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserResponseSchema:
        user_id = int(input_data['user_id'])
        new_status = input_data['status']
        
        # Check if user exists using repository
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # Prepare update data with audit context
        update_data = self._add_audit_context({'status': new_status}, user, ctx)
        
        # Update using repository (includes cache invalidation)
        updated_user = await self.user_repository.update(user_id, update_data)
        
        if not updated_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="Failed to change user status."
            )
        
        return UserResponseSchema.model_validate(updated_user)


class VerifyPasswordUseCase(BaseUseCase):
    """Verify user password using repository's verify_password business function"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True

    async def _validate_input(self, input_data, ctx):
        user_id = input_data.get('user_id')
        password = input_data.get('password')
        
        if not user_id or not password:
            raise UserNotFoundException(
                user_message="User ID and password are required."
            )
        
        try:
            int(user_id)
        except (ValueError, TypeError):
            raise UserNotFoundException(
                user_id=user_id,
                user_message="Invalid user ID format."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Dict[str, Any]:
        user_id = int(input_data['user_id'])
        password = input_data['password']
        
        # Use repository's verify_password business function
        is_valid = await self.user_repository.verify_password(user_id, password)
        
        return {
            "user_id": user_id,
            "password_valid": is_valid,
            "message": "Password verification completed"
        }