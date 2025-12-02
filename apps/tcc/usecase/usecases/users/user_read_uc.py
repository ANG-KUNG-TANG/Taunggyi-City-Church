from typing import Dict, Any, List
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import UserNotFoundException
from apps.tcc.models.base.enums import UserRole
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema, UserListResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase


class GetUserByIdUseCase(BaseUseCase):
    """Get user by ID using repository's get_by_id with caching"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True

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
        
        # Use repository's get_by_id (includes caching)
        user_entity = await self.user_repository.get_by_id(user_id)
        
        if not user_entity:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        return UserResponseSchema.model_validate(user_entity)


class GetUserByEmailUseCase(BaseUseCase):
    """Get user by email using repository's get_by_email with caching"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True

    async def _validate_input(self, input_data, ctx):
        email = input_data.get('email')
        if not email:
            raise UserNotFoundException(
                email=email,
                user_message="Email is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserResponseSchema:
        email = input_data['email']
        
        # Use repository's get_by_email (includes caching)
        user_entity = await self.user_repository.get_by_email(email)
        
        if not user_entity:
            raise UserNotFoundException(
                email=email,
                user_message="User with this email not found."
            )
        
        return UserResponseSchema.model_validate(user_entity)


class GetAllUsersUseCase(BaseUseCase):
    """Get all users with pagination using repository's get_paginated_users"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserListResponseSchema:
        filters = input_data.get('filters', {})
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        # Use repository's get_paginated_users (includes caching and filtering)
        users, total_count = await self.user_repository.get_paginated_users(
            filters=filters,
            page=page,
            per_page=per_page
        )
        
        # Convert to response schemas
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
    """Get users by role using repository's get_paginated_users with role filter"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']
        self.config.validate_input = True

    async def _validate_input(self, input_data, ctx):
        role = input_data.get('role')
        if not role:
            raise UserNotFoundException(
                user_message="Role is required."
            )
        
        # Validate role
        if isinstance(role, str):
            try:
                UserRole(role)  # Validate it's a valid role
            except ValueError:
                valid_roles = [role.value for role in UserRole]
                raise UserNotFoundException(
                    user_message=f"Invalid role. Valid roles: {', '.join(valid_roles)}"
                )

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserListResponseSchema:
        role = input_data['role']
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        # Use repository's get_paginated_users with role filter
        users, total_count = await self.user_repository.get_paginated_users(
            filters={'role': role},
            page=page,
            per_page=per_page
        )
        
        user_responses = [UserResponseSchema.model_validate(user) for user in users]
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
    """Search users using repository's search_users business function"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']
        self.config.validate_input = True

    async def _validate_input(self, input_data, ctx):
        search_term = input_data.get('search_term')
        if not search_term or len(search_term.strip()) < 2:
            raise UserNotFoundException(
                user_message="Search term must be at least 2 characters long."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserListResponseSchema:
        search_term = input_data['search_term']
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        # Use repository's search_users business function
        users, total_count = await self.user_repository.search_users(
            search_term=search_term,
            page=page,
            per_page=per_page
        )
        
        user_responses = [UserResponseSchema.model_validate(user) for user in users]
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