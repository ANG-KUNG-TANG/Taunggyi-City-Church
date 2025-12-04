from typing import Dict, Any
from apps.core.core_exceptions.domain import DomainValidationException
from apps.core.schemas.input_schemas.users import EmailCheckInputSchema, UserQueryInputSchema, UserSearchInputSchema
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import UserNotFoundException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.schemas.out_schemas.user_out_schemas import EmailCheckResponseSchema, UserListResponseSchema, UserResponseSchema, UserSearchResponseSchema, UserSimpleResponseSchema
import logging

logger = logging.getLogger(__name__)

class GetUserByIdUseCase(BaseUseCase):
    """Get user by ID - Returns UserResponseSchema"""
    
    def __init__(self, user_repository: UserRepository = None, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository or UserRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserResponseSchema:
        """Get user by ID - Returns Schema"""
        user_id = await self._validate_entity_id(
            input_data.get('user_id'),
            "User ID"
        )
        
        # Business rule: Users can only view their own profile unless they have permission
        if not await self._can_view_user(user, user_id):
            raise DomainValidationException(
                "Insufficient permissions to view this user",
                user_message="You do not have permission to view this user."
            )
        
        user_entity = await self.user_repository.get_by_id(user_id)
        if not user_entity:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        return UserResponseSchema.model_validate(user_entity)
    
    async def _can_view_user(self, current_user, target_user_id: int) -> bool:
        """Business rule: Check if user can view target user"""
        if not current_user:
            return False
            
        # User can always view their own profile
        if hasattr(current_user, 'id') and current_user.id == target_user_id:
            return True
            
        # Users with view permissions can view others
        if hasattr(current_user, 'has_permission') and current_user.has_permission('can_view_users'):
            return True
            
        return False

class GetUserByEmailUseCase(BaseUseCase):
    """Get user by email - Returns UserResponseSchema"""
    
    def __init__(self, user_repository: UserRepository = None, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository or UserRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserResponseSchema:
        """Get user by email - Returns Schema"""
        email_input = EmailCheckInputSchema(**input_data)
        
        user_entity = await self.user_repository.get_by_email(email_input.email)
        if not user_entity:
            raise UserNotFoundException(
                email=email_input.email,
                user_message="User not found."
            )
        
        # Business rule: Hide sensitive info unless self or admin
        if not await self._can_view_sensitive_info(user, user_entity.id):
            # Return limited info
            return UserSimpleResponseSchema.model_validate(user_entity)
        
        return UserResponseSchema.model_validate(user_entity)
    
    async def _can_view_sensitive_info(self, current_user, target_user_id: int) -> bool:
        """Business rule: Check if user can view sensitive user info"""
        if not current_user:
            return False
            
        # User can view their own sensitive info
        if hasattr(current_user, 'id') and current_user.id == target_user_id:
            return True
            
        # Admins can view sensitive info
        if hasattr(current_user, 'is_superuser') and current_user.is_superuser:
            return True
            
        return False

class ListUsersUseCase(BaseUseCase):
    """List users with pagination - Returns UserListResponseSchema"""
    
    def __init__(self, user_repository: UserRepository = None, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository or UserRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_view_users']
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserListResponseSchema:
        """List users - Returns Paginated Schema"""
        query_input = UserQueryInputSchema(**input_data)
        
        # Apply business rules to filters
        filters = query_input.model_dump(exclude={'page', 'per_page', 'sort_by', 'sort_order'})
        
        # Business rule: Non-admins can only see active users
        if not (hasattr(user, 'is_superuser') and user.is_superuser):
            filters['is_active'] = True
        
        # Get paginated results
        users, total_count = await self.user_repository.get_paginated(
            filters=filters,
            page=query_input.page,
            per_page=query_input.per_page
        )
        
        # Convert to simple schemas for list view
        items = [UserSimpleResponseSchema.model_validate(user) for user in users]
        
        return UserListResponseSchema(
            items=items,
            total=total_count,
            page=query_input.page,
            page_size=query_input.per_page,
            total_pages=(total_count + query_input.per_page - 1) // query_input.per_page if query_input.per_page > 0 else 1
        )

class SearchUsersUseCase(BaseUseCase):
    """Search users - Returns UserSearchResponseSchema"""
    
    def __init__(self, user_repository: UserRepository = None, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository or UserRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_view_users']
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserSearchResponseSchema:
        """Search users - Returns Paginated Schema"""
        search_input = UserSearchInputSchema(**input_data)
        
        users, total_count = await self.user_repository.search_users(
            search_input.search_term,
            page=search_input.page,
            per_page=search_input.per_page
        )
        
        items = [UserSimpleResponseSchema.model_validate(user) for user in users]
        
        return UserSearchResponseSchema(
            items=items,
            total=total_count,
            page=search_input.page,
            page_size=search_input.per_page,
            search_term=search_input.search_term,
            total_pages=(total_count + search_input.per_page - 1) // search_input.per_page if search_input.per_page > 0 else 1
        )


class CheckEmailExistsUseCase(BaseUseCase):
    """Check if email exists - Returns EmailCheckResponseSchema"""
    
    def __init__(self, user_repository: UserRepository = None, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository or UserRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Public endpoint
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> EmailCheckResponseSchema:
        """Check email - Returns Schema"""
        email_input = EmailCheckInputSchema(**input_data)
        
        exists = await self.user_repository.email_exists(email_input.email)
        
        return EmailCheckResponseSchema(
            email=email_input.email,
            exists=exists,
            available=not exists
        )

