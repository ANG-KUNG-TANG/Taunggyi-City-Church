from typing import Dict, Any
from usecases.base.base_uc  import OperationPortalUseCase
from usecase.exceptions.u_exceptions import (
    InvalidUserInputError,
    UserNotFoundException
)
from entities.users import UserEntity
from apps.tcc.models.base.enums import UserStatus

class UpdateUserUseCase(OperationPortalUseCase):
    """Use case for updating user profile"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    def _validate_input(self, input_data: Dict[str, Any], context):
        user_id = input_data.get('user_id')
        if not user_id:
            raise InvalidUserInputError(details={
                "message": "User ID is required",
                "field": "user_id"
            })

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        user_id = input_data['user_id']
        
        # Check if user exists
        existing_user = self.user_repository.get_by_id(user_id, user)
        if not existing_user:
            raise UserNotFoundException(user_id=user_id)
        
        # Create updated user entity
        updated_entity = UserEntity(
            id=user_id,
            name=input_data.get('name', existing_user.name),
            email=input_data.get('email', existing_user.email),
            phone_number=input_data.get('phone_number', existing_user.phone_number),
            age=input_data.get('age', existing_user.age),
            gender=input_data.get('gender', existing_user.gender),
            marital_status=input_data.get('marital_status', existing_user.marital_status),
            date_of_birth=input_data.get('date_of_birth', existing_user.date_of_birth),
            testimony=input_data.get('testimony', existing_user.testimony),
            baptism_date=input_data.get('baptism_date', existing_user.baptism_date),
            membership_date=input_data.get('membership_date', existing_user.membership_date),
            role=input_data.get('role', existing_user.role),
            status=input_data.get('status', existing_user.status),
            email_notifications=input_data.get('email_notifications', existing_user.email_notifications),
            sms_notifications=input_data.get('sms_notifications', existing_user.sms_notifications)
        )
        
        # Update user
        updated_user = self.user_repository.update(user_id, updated_entity, user)
        
        if not updated_user:
            raise UserNotFoundException(user_id=user_id)
        
        return {
            "message": "User updated successfully",
            "user": {
                'id': updated_user.id,
                'name': updated_user.name,
                'email': updated_user.email,
                'role': updated_user.role,
                'status': updated_user.status
            }
        }

class ChangeUserStatusUseCase(OperationPortalUseCase):
    """Use case for changing user status (admin only)"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    def _validate_input(self, input_data: Dict[str, Any], context):
        user_id = input_data.get('user_id')
        status = input_data.get('status')
        
        if not user_id:
            raise InvalidUserInputError(details={
                "message": "User ID is required",
                "field": "user_id"
            })
        
        if not status:
            raise InvalidUserInputError(details={
                "message": "Status is required",
                "field": "status"
            })
        
        if status not in [status.value for status in UserStatus]:
            raise InvalidUserInputError(details={
                "message": "Invalid status",
                "field": "status",
                "valid_statuses": [status.value for status in UserStatus]
            })

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        user_id = input_data['user_id']
        status = input_data['status']
        
        updated_user = self.user_repository.change_user_status(user_id, status, user)
        
        if not updated_user:
            raise UserNotFoundException(user_id=user_id)
        
        return {
            "message": "User status updated successfully",
            "user": {
                'id': updated_user.id,
                'name': updated_user.name,
                'email': updated_user.email,
                'status': updated_user.status
            }
        }