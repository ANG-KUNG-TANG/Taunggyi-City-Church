from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserNotFoundException
)
from entities.users import UserEntity
from apps.tcc.models.base.enums import UserRole, UserStatus

class CreateUserUseCase(BaseUseCase):
    """Use case for creating new users"""
    
    def __init__(self):
        super().__init__()
        self.user_repository = UserRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        required_fields = ['name', 'email']
        missing_fields = [field for field in required_fields if not input_data.get(field)]
        
        if missing_fields:
            raise InvalidUserInputException(details={
                "message": "Missing required fields",
                "fields": missing_fields
            })
        
        # Check if email already exists
        if await self.user_repository.email_exists(input_data['email']):
            raise InvalidUserInputException(details={
                "message": "Email already exists",
                "field": "email"
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
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
            role=input_data.get('role', UserRole.MEMBER),
            status=input_data.get('status', UserStatus.ACTIVE),
            email_notifications=input_data.get('email_notifications', True),
            sms_notifications=input_data.get('sms_notifications', False)
        )
        
        # Create user using repository's create method
        created_user = await self.user_repository.create(user_entity)
        
        return {
            "message": "User created successfully",
            "user": {
                'id': created_user.id,
                'name': created_user.name,
                'email': created_user.email,
                'role': created_user.role.value if hasattr(created_user.role, 'value') else created_user.role,
                'status': created_user.status.value if hasattr(created_user.status, 'value') else created_user.status
            }
        }