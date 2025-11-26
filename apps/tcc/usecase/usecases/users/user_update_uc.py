from typing import Dict, Any, List
from apps.core.schemas.builders.user_rp_builder import UserResponseBuilder
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserNotFoundException
)
from apps.tcc.usecase.entities.users import UserEntity
from apps.core.schemas.schemas.users import UserUpdateSchema
from apps.tcc.models.base.enums import UserStatus


class UpdateUserUseCase(BaseUseCase):
    """Fixed use case for updating user profile"""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True

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
        
        # Validate update data using schema
        update_data = input_data.get('update_data', {})
        try:
            UserUpdateSchema(**update_data)
        except Exception as e:
            field_errors = self._extract_pydantic_errors(e)
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message="Please check your update data and try again."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        user_id = int(input_data['user_id'])
        update_data = input_data.get('update_data', {})
        
        # Check if user exists
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # Create updated UserEntity by merging existing data with updates
        updated_entity_data = {**existing_user.__dict__, **update_data}
        updated_entity = UserEntity(**updated_entity_data)
        
        # Update user using repository
        updated_user = await self.user_repository.update(user_id, updated_entity)
        
        if not updated_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="Failed to update user."
            )
        
        # Use builder for response
        user_response = UserResponseBuilder.to_response(updated_user)
        
        return APIResponse.success_response(
            message="User updated successfully",
            data=user_response.model_dump()
        )

    def _extract_pydantic_errors(self, validation_error: Exception) -> Dict[str, List[str]]:
        """Extract field errors from Pydantic validation"""
        field_errors = {}
        if hasattr(validation_error, 'errors'):
            for error in validation_error.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                field_errors.setdefault(field, []).append(error['msg'])
        else:
            field_errors['_form'] = [str(validation_error)]
        return field_errors


class ChangeUserStatusUseCase(BaseUseCase):
    """Fixed use case for changing user status"""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        user_id = input_data.get('user_id')
        status = input_data.get('status')
        
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
        
        if not status:
            raise InvalidUserInputException(
                field_errors={"status": ["Status is required"]},
                user_message="Please specify a status."
            )
        
        # Convert string to enum if needed
        if isinstance(status, str):
            try:
                status = UserStatus(status)
            except ValueError:
                valid_statuses = [status.value for status in UserStatus]
                raise InvalidUserInputException(
                    field_errors={"status": [f"Invalid status. Valid statuses: {', '.join(valid_statuses)}"]},
                    user_message="Please provide a valid user status."
                )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        user_id = int(input_data['user_id'])
        status = input_data['status']
        
        # Get existing user
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # Create updated entity with only status changed
        updated_entity_data = {**existing_user.__dict__, 'status': status}
        updated_entity = UserEntity(**updated_entity_data)
        
        # Update user using repository
        updated_user = await self.user_repository.update(user_id, updated_entity)
        
        if not updated_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="Failed to update user status."
            )
        
        user_response = UserResponseBuilder.to_response(updated_user)
        
        return APIResponse.success_response(
            message="User status updated successfully",
            data=user_response.model_dump()
        )