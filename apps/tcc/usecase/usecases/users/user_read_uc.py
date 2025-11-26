from typing import Dict, Any, List
from apps.core.schemas.builders.user_rp_builder import UserResponseBuilder
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserNotFoundException
)
from apps.tcc.models.base.enums import UserRole


class GetUserByIdUseCase(BaseUseCase):
    """Fixed use case for getting user by ID"""
    
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

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        user_id = int(input_data['user_id'])
        user_entity = await self.user_repository.get_by_id(user_id)
        
        if not user_entity:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # Use builder to create consistent response
        user_response = UserResponseBuilder.to_response(user_entity)
        
        return APIResponse.success_response(
            message="User retrieved successfully",
            data=user_response.model_dump()
        )


class GetUserByEmailUseCase(BaseUseCase):
    """Fixed use case for getting user by email"""
    
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

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        email = input_data['email']
        user_entity = await self.user_repository.get_by_email(email)
        
        if not user_entity:
            raise UserNotFoundException(
                email=email,
                user_message="User with this email not found."
            )
        
        user_response = UserResponseBuilder.to_response(user_entity)
        
        return APIResponse.success_response(
            message="User retrieved successfully",
            data=user_response.model_dump()
        )


class GetAllUsersUseCase(BaseUseCase):
    """Fixed use case for getting all users with pagination"""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        filters = input_data.get('filters', {})
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        # Get users with pagination using correct repository method
        users, total_count = await self.user_repository.get_paginated_users(
            filters=filters,
            page=page,
            per_page=per_page
        )
        
        # Use builder for list response
        list_response = UserResponseBuilder.to_list_response(
            entities=users,
            total=total_count,
            page=page,
            per_page=per_page
        )
        
        return APIResponse.success_response(
            message="Users retrieved successfully",
            data=list_response.model_dump()
        )


class GetUsersByRoleUseCase(BaseUseCase):
    """Fixed use case for getting users by role"""
    
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

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        role = input_data['role']
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        # Use filters with role instead of role-specific method
        users, total_count = await self.user_repository.get_paginated_users(
            filters={'role': role},
            page=page,
            per_page=per_page
        )
        
        list_response = UserResponseBuilder.to_list_response(
            entities=users,
            total=total_count,
            page=page,
            per_page=per_page
        )
        
        return APIResponse.success_response(
            message=f"Users with role {role.value} retrieved successfully",
            data=list_response.model_dump()
        )


class SearchUsersUseCase(BaseUseCase):
    """Fixed use case for searching users"""
    
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

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        search_term = input_data['search_term']
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        users, total_count = await self.user_repository.search_users(
            search_term=search_term,
            page=page,
            per_page=per_page
        )
        
        list_response = UserResponseBuilder.to_list_response(
            entities=users,
            total=total_count,
            page=page,
            per_page=per_page
        )
        
        return APIResponse.success_response(
            message=f"Search results for '{search_term}'",
            data=list_response.model_dump()
        )