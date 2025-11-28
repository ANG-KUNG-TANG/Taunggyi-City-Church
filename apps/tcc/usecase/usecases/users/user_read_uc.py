from typing import Dict, Any, List
from apps.core.schemas.out_schemas.base import BaseResponseSchema
from apps.core.schemas.common.pagination import PaginatedResponse
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserNotFoundException
)
from apps.tcc.models.base.enums import UserRole
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema, UserListResponseSchema

class GetUserByIdUseCase(BaseUseCase):
    """Use case for getting user by ID - without builder pattern"""
    
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

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> UserResponseSchema:
        user_id = int(input_data['user_id'])
        user_entity = await self.user_repository.get_by_id(user_id)
        
        if not user_entity:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # Convert entity directly to response schema
        return UserResponseSchema.model_validate(user_entity)


class GetUserByEmailUseCase(BaseUseCase):
    """Use case for getting user by email - without builder pattern"""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        email = input_data.get('email')
        if not email:
            raise InvalidUserInputException(
                field_errors={"email": ["Email is required"]},
                user_message="Please provide a valid email address."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> UserResponseSchema:
        email = input_data['email']
        user_entity = await self.user_repository.get_by_email(email)
        
        if not user_entity:
            raise UserNotFoundException(
                email=email,
                user_message="User with this email not found."
            )
        
        # Convert entity directly to response schema
        return UserResponseSchema.model_validate(user_entity)


class GetAllUsersUseCase(BaseUseCase):
    """Use case for getting all users with pagination - without builder pattern"""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> UserListResponseSchema:
        filters = input_data.get('filters', {})
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        # Get users with pagination using correct repository method
        users, total_count = await self.user_repository.get_paginated_users(
            filters=filters,
            page=page,
            per_page=per_page
        )
        
        # Convert entities directly to response schemas
        user_responses = [UserResponseSchema.model_validate(user) for user in users]
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 1
        
        return UserListResponseSchema(
            items=user_responses,
            total=total_count,
            page=page,
            page_size=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


class GetUsersByRoleUseCase(BaseUseCase):
    """Use case for getting users by role - without builder pattern"""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        role = input_data.get('role')
        if not role:
            raise InvalidUserInputException(
                field_errors={"role": ["Role is required"]},
                user_message="Please specify a user role."
            )
        
        # Convert string to enum if needed
        if isinstance(role, str):
            try:
                role = UserRole(role)
            except ValueError:
                valid_roles = [role.value for role in UserRole]
                raise InvalidUserInputException(
                    field_errors={"role": [f"Invalid role. Valid roles: {', '.join(valid_roles)}"]},
                    user_message="Please provide a valid user role."
                )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> UserListResponseSchema:
        role = input_data['role']
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        # Use filters with role instead of role-specific method
        users, total_count = await self.user_repository.get_paginated_users(
            filters={'role': role},
            page=page,
            per_page=per_page
        )
        
        # Convert entities directly to response schemas
        user_responses = [UserResponseSchema.model_validate(user) for user in users]
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 1
        
        return UserListResponseSchema(
            items=user_responses,
            total=total_count,
            page=page,
            page_size=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


class SearchUsersUseCase(BaseUseCase):
    """Use case for searching users - without builder pattern"""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        search_term = input_data.get('search_term')
        if not search_term or len(search_term.strip()) < 2:
            raise InvalidUserInputException(
                field_errors={"search_term": ["Search term must be at least 2 characters long"]},
                user_message="Please provide a search term with at least 2 characters."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> UserListResponseSchema:
        search_term = input_data['search_term']
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        users, total_count = await self.user_repository.search_users(
            search_term=search_term,
            page=page,
            per_page=per_page
        )
        
        # Convert entities directly to response schemas
        user_responses = [UserResponseSchema.model_validate(user) for user in users]
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 1
        
        return UserListResponseSchema(
            items=user_responses,
            total=total_count,
            page=page,
            page_size=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )