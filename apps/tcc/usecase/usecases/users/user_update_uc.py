from typing import Dict, Any
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserNotFoundException
)
from entities.users import UserEntity
from apps.tcc.models.base.enums import UserStatus

class UpdateUserUseCase(BaseUseCase):
    """Use case for updating user profile"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        user_id = input_data.get('user_id')
        if not user_id:
            raise InvalidUserInputException(details={
                "message": "User ID is required",
                "field": "user_id"
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        user_id = input_data['user_id']
        
        # Check if user exists
        existing_user = await self.user_repository.get_by_id(user_id, user)
        if not existing_user:
            raise UserNotFoundException(user_id=user_id)
        
        # Prepare update data
        update_data = {
            'name': input_data.get('name', existing_user.name),
            'email': input_data.get('email', existing_user.email),
            'phone_number': input_data.get('phone_number', existing_user.phone_number),
            'age': input_data.get('age', existing_user.age),
            'gender': input_data.get('gender', existing_user.gender),
            'marital_status': input_data.get('marital_status', existing_user.marital_status),
            'date_of_birth': input_data.get('date_of_birth', existing_user.date_of_birth),
            'testimony': input_data.get('testimony', existing_user.testimony),
            'baptism_date': input_data.get('baptism_date', existing_user.baptism_date),
            'membership_date': input_data.get('membership_date', existing_user.membership_date),
            'role': input_data.get('role', existing_user.role),
            'status': input_data.get('status', existing_user.status),
            'email_notifications': input_data.get('email_notifications', existing_user.email_notifications),
            'sms_notifications': input_data.get('sms_notifications', existing_user.sms_notifications)
        }
        
        # Update user using repository
        updated_user = await self.user_repository.update(user_id, update_data, user)
        
        if not updated_user:
            raise UserNotFoundException(user_id=user_id)
        
        return {
            "message": "User updated successfully",
            "user": {
                'id': updated_user.id,
                'name': updated_user.name,
                'email': updated_user.email,
                'role': updated_user.role.value if hasattr(updated_user.role, 'value') else updated_user.role,
                'status': updated_user.status.value if hasattr(updated_user.status, 'value') else updated_user.status
            }
        }

class ChangeUserStatusUseCase(BaseUseCase):
    """Use case for changing user status (admin only)"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        user_id = input_data.get('user_id')
        status = input_data.get('status')
        
        if not user_id:
            raise InvalidUserInputException(details={
                "message": "User ID is required",
                "field": "user_id"
            })
        
        if not status:
            raise InvalidUserInputException(details={
                "message": "Status is required",
                "field": "status"
            })
        
        # Convert string to enum if needed
        if isinstance(status, str):
            try:
                status = UserStatus(status)
            except ValueError:
                valid_statuses = [status.value for status in UserStatus]
                raise InvalidUserInputException(details={
                    "message": "Invalid status",
                    "field": "status",
                    "valid_statuses": valid_statuses
                })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        user_id = input_data['user_id']
        status = input_data['status']
        
        updated_user = await self.user_repository.change_user_status(user_id, status, user)
        
        if not updated_user:
            raise UserNotFoundException(user_id=user_id)
        
        return {
            "message": "User status updated successfully",
            "user": {
                'id': updated_user.id,
                'name': updated_user.name,
                'email': updated_user.email,
                'status': updated_user.status.value if hasattr(updated_user.status, 'value') else updated_user.status
            }
        }