from typing import Dict, Any, List, Optional
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserNotFoundException
)
from apps.tcc.models.base.enums import UserRole, UserStatus

class GetUserByIdUseCase(BaseUseCase):
    """Use case for getting user by ID"""
    
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
        user_entity = await self.user_repository.get_by_id(user_id, user)
        
        if not user_entity:
            raise UserNotFoundException(user_id=user_id)
        
        return self._format_user_response(user_entity)

class GetUserByEmailUseCase(BaseUseCase):
    """Use case for getting user by email"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        email = input_data.get('email')
        if not email:
            raise InvalidUserInputException(details={
                "message": "Email is required",
                "field": "email"
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        email = input_data['email']
        user_entity = await self.user_repository.get_by_email(email, user)
        
        if not user_entity:
            raise UserNotFoundException(message=f"User with email {email} not found")
        
        return self._format_user_response(user_entity)

class GetAllUsersUseCase(BaseUseCase):
    """Use case for getting all users with optional filtering"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        filters = input_data.get('filters', {})
        users = await self.user_repository.get_all(user, filters)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "total_count": len(users)
        }

class GetUsersByRoleUseCase(BaseUseCase):
    """Use case for getting users by role"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        role = input_data.get('role')
        if not role:
            raise InvalidUserInputException(details={
                "message": "Role is required",
                "field": "role"
            })
        
        # Convert string to enum if needed
        if isinstance(role, str):
            try:
                role = UserRole(role)
            except ValueError:
                valid_roles = [role.value for role in UserRole]
                raise InvalidUserInputException(details={
                    "message": "Invalid role",
                    "field": "role",
                    "valid_roles": valid_roles
                })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        role = input_data['role']
        users = await self.user_repository.get_by_role(role, user)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "role": role.value if hasattr(role, 'value') else role,
            "total_count": len(users)
        }

class SearchUsersUseCase(BaseUseCase):
    """Use case for searching users"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        search_term = input_data.get('search_term')
        if not search_term:
            raise InvalidUserInputException(details={
                "message": "Search term is required",
                "field": "search_term"
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        search_term = input_data['search_term']
        users = await self.user_repository.search_users(search_term, user)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "search_term": search_term,
            "total_count": len(users)
        }

class GetMinistryLeadersUseCase(BaseUseCase):
    """Use case for getting all ministry leaders"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        users = await self.user_repository.get_ministry_leaders(user)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "total_count": len(users)
        }

class GetUsersByStatusUseCase(BaseUseCase):
    """Use case for getting users by status"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        status = input_data.get('status')
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
        status = input_data['status']
        users = await self.user_repository.get_users_by_status(status, user)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "status": status.value if hasattr(status, 'value') else status,
            "total_count": len(users)
        }

class GetActiveUsersCountUseCase(BaseUseCase):
    """Use case for getting active users count"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        count = await self.user_repository.get_active_users_count()
        
        return {
            "active_users_count": count
        }

# Common response formatting method
def _format_user_response(user_entity):
    """Format user entity for response"""
    return {
        'id': user_entity.id,
        'name': user_entity.name,
        'email': user_entity.email,
        'phone_number': user_entity.phone_number,
        'age': user_entity.age,
        'gender': user_entity.gender,
        'marital_status': user_entity.marital_status,
        'date_of_birth': user_entity.date_of_birth,
        'role': user_entity.role.value if hasattr(user_entity.role, 'value') else user_entity.role,
        'status': user_entity.status.value if hasattr(user_entity.status, 'value') else user_entity.status,
        'is_active': user_entity.is_active,
        'email_notifications': user_entity.email_notifications,
        'sms_notifications': user_entity.sms_notifications,
        'membership_date': user_entity.membership_date,
        'baptism_date': user_entity.baptism_date,
        'created_at': user_entity.created_at,
        'updated_at': user_entity.updated_at
    }

# Attach the formatting method to all read use cases
for cls in [GetUserByIdUseCase, GetUserByEmailUseCase, GetAllUsersUseCase, 
           GetUsersByRoleUseCase, SearchUsersUseCase, GetMinistryLeadersUseCase,
           GetUsersByStatusUseCase]:
    cls._format_user_response = staticmethod(_format_user_response)