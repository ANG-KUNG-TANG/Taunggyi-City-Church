from typing import Dict, Any, List, Optional
from usecases.base.base_uc  import OperationPortalUseCase
from usecase.exceptions.u_exceptions import (
    InvalidUserInputError,
    UserNotFoundException
)
from apps.tcc.models.base.enums import UserRole, UserStatus

class GetUserByIdUseCase(OperationPortalUseCase):
    """Use case for getting user by ID"""
    
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
        user_entity = self.user_repository.get_by_id(user_id, user)
        
        if not user_entity:
            raise UserNotFoundException(user_id=user_id)
        
        return self._format_user_response(user_entity)

class GetUserByEmailUseCase(OperationPortalUseCase):
    """Use case for getting user by email"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    def _validate_input(self, input_data: Dict[str, Any], context):
        email = input_data.get('email')
        if not email:
            raise InvalidUserInputError(details={
                "message": "Email is required",
                "field": "email"
            })

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        email = input_data['email']
        user_entity = self.user_repository.get_by_email(email, user)
        
        if not user_entity:
            raise UserNotFoundException(message=f"User with email {email} not found")
        
        return self._format_user_response(user_entity)

class GetAllUsersUseCase(OperationPortalUseCase):
    """Use case for getting all users with optional filtering"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        filters = input_data.get('filters', {})
        users = self.user_repository.get_all(user, filters)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "total_count": len(users)
        }

class GetUsersByRoleUseCase(OperationPortalUseCase):
    """Use case for getting users by role"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    def _validate_input(self, input_data: Dict[str, Any], context):
        role = input_data.get('role')
        if not role:
            raise InvalidUserInputError(details={
                "message": "Role is required",
                "field": "role"
            })
        
        if role not in [role.value for role in UserRole]:
            raise InvalidUserInputError(details={
                "message": "Invalid role",
                "field": "role",
                "valid_roles": [role.value for role in UserRole]
            })

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        role = input_data['role']
        users = self.user_repository.get_by_role(role, user)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "role": role,
            "total_count": len(users)
        }

class SearchUsersUseCase(OperationPortalUseCase):
    """Use case for searching users"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    def _validate_input(self, input_data: Dict[str, Any], context):
        search_term = input_data.get('search_term')
        if not search_term:
            raise InvalidUserInputError(details={
                "message": "Search term is required",
                "field": "search_term"
            })

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        search_term = input_data['search_term']
        users = self.user_repository.search_users(search_term, user)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "search_term": search_term,
            "total_count": len(users)
        }

class GetMinistryLeadersUseCase(OperationPortalUseCase):
    """Use case for getting all ministry leaders"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        users = self.user_repository.get_ministry_leaders(user)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "total_count": len(users)
        }

class GetUsersByStatusUseCase(OperationPortalUseCase):
    """Use case for getting users by status"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    def _validate_input(self, input_data: Dict[str, Any], context):
        status = input_data.get('status')
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
        status = input_data['status']
        users = self.user_repository.get_users_by_status(status, user)
        
        return {
            "users": [self._format_user_response(user_entity) for user_entity in users],
            "status": status,
            "total_count": len(users)
        }

class GetActiveUsersCountUseCase(OperationPortalUseCase):
    """Use case for getting active users count"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        count = self.user_repository.get_active_users_count()
        
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
        'role': user_entity.role,
        'status': user_entity.status,
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