from typing import Dict, Any
from usecases.base.base_uc  import OperationPortalUseCase
from usecase.exceptions.u_exceptions import (
    InvalidUserInputError,
)
from entities.users import UserEntity

class CreateUserUseCase(OperationPortalUseCase):
    """Use case for creating new users"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    def _validate_input(self, input_data: Dict[str, Any], context):
        required_fields = ['name', 'email', 'password']
        missing_fields = [field for field in required_fields if not input_data.get(field)]
        
        if missing_fields:
            raise InvalidUserInputError(details={
                "message": "Missing required fields",
                "fields": missing_fields
            })
        
        # Check if email already exists
        if self.user_repository.email_exists(input_data['email']):
            raise InvalidUserInputError(details={
                "message": "Email already exists",
                "field": "email"
            })

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        # Convert input to UserEntity
        user_entity = UserEntity(
            name=input_data['name'],
            email=input_data['email'],
            phone_number=input_data.get('phone_number'),
            age=input_data.get('age'),
            gender=input_data.get('gender'),
            marital_status=input_data.get('marital_status'),
            date_of_birth=input_data.get('date_of_birth'),
            testimony=input_data.get('testimony'),
            baptism_date=input_data.get('baptism_date'),
            membership_date=input_data.get('membership_date'),
            role=input_data.get('role', 'MEMBER'),  # Default role
            status=input_data.get('status', 'ACTIVE'),  # Default status
            email_notifications=input_data.get('email_notifications', True),
        )
        
        # Create user
        created_user = self.user_repository.create(user_entity, user)
        
        return {
            "message": "User created successfully",
            "user": {
                'id': created_user.id,
                'name': created_user.name,
                'email': created_user.email,
                'role': created_user.role,
                'status': created_user.status
            }
        }