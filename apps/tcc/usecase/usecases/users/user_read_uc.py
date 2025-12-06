from typing import Dict, Any, List, Tuple
from apps.core.core_exceptions.domain import DomainValidationException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import UserNotFoundException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.schemas.input_schemas.users import (
    UserQueryInputSchema,
    UserSearchInputSchema,
    EmailCheckInputSchema
)
from apps.tcc.usecase.entities.users_entity import UserEntity
from apps.core.schemas.out_schemas.user_out_schemas import EmailCheckResponseSchema
import logging

logger = logging.getLogger(__name__)


class GetUserByIdUseCase(BaseUseCase):
    """Get user by ID - Returns UserEntity"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserEntity:
        """Get user by ID - Returns Entity"""
        user_id = input_data.get('user_id')
        if not user_id:
            raise DomainValidationException("User ID is required")
        
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise DomainValidationException("Invalid User ID format")
        
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
        
        return user_entity
    
    async def _can_view_user(self, current_user, target_user_id: int) -> bool:
        """Business rule: Check if user can view target user"""
        if not current_user:
            return False
            
        # User can always view their own profile
        if hasattr(current_user, 'id') and current_user.id == target_user_id:
            return True
            
        # Users with view permissions can view others
        if hasattr(current_user, 'has_permission') and callable(current_user.has_permission):
            return current_user.has_permission('can_view_users')
            
        return False


class GetUserByEmailUseCase(BaseUseCase):
    """Get user by email - Returns UserEntity"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserEntity:
        """Get user by email - Returns Entity"""
        email_input = EmailCheckInputSchema(**input_data)
        
        user_entity = await self.user_repository.get_by_email(email_input.email)
        if not user_entity:
            raise UserNotFoundException(
                email=email_input.email,
                user_message="User not found."
            )
        
        # Business rule: Hide sensitive info unless self or admin
        if not await self._can_view_sensitive_info(user, user_entity.id):
            # Create a safe copy without sensitive info
            safe_entity = UserEntity(
                id=user_entity.id,
                name=user_entity.name,
                is_active=user_entity.is_active,
                role=user_entity.role,
                # Hide sensitive fields
                email=None,
                phone=None,
                address=None,
                created_at=user_entity.created_at,
                updated_at=user_entity.updated_at
            )
            return safe_entity
        
        return user_entity
    
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
    """Get all users with pagination - Returns Tuple[List[UserEntity], int]"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_view_users']
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Tuple[List[UserEntity], int]:
        """Get all users - Returns Tuple of UserEntities and total count"""
        query_input = UserQueryInputSchema(**input_data)
        
        # Apply business rules to filters
        filters = query_input.model_dump(exclude={'page', 'per_page', 'sort_by', 'sort_order'})
        
        # Business rule: Non-admins can only see active users
        if not (hasattr(user, 'is_superuser') and user.is_superuser):
            filters['is_active'] = True
        
        # Get paginated results from repository
        users, total_count = await self.user_repository.get_paginated(
            filters=filters,
            page=query_input.page,
            per_page=query_input.per_page
        )
        
        return users, total_count


class GetUsersByRoleUseCase(BaseUseCase):
    """Get users by role with pagination - Returns Tuple[List[UserEntity], int]"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_view_users']
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Tuple[List[UserEntity], int]:
        """Get users by role - Returns Tuple of UserEntities and total count"""
        role = input_data.get('role')
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        if not role:
            raise ValueError("Role is required")
        
        # Build filters
        filters = {'role': role}
        
        # Business rule: Non-admins can only see active users
        if not (hasattr(user, 'is_superuser') and user.is_superuser):
            filters['is_active'] = True
        
        # Get paginated results from repository
        users, total_count = await self.user_repository.get_paginated(
            filters=filters,
            page=page,
            per_page=per_page
        )
        
        return users, total_count


class SearchUsersUseCase(BaseUseCase):
    """Search users - Returns Tuple[List[UserEntity], int]"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_view_users']
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Tuple[List[UserEntity], int]:
        """Search users - Returns Tuple of UserEntities and total count"""
        search_input = UserSearchInputSchema(**input_data)
        
        # Search using repository
        users, total_count = await self.user_repository.search_users(
            search_input.search_term,
            page=search_input.page,
            per_page=search_input.per_page
        )
        
        return users, total_count


class CheckEmailExistsUseCase(BaseUseCase):
    """Check if email exists - Returns EmailCheckResponseSchema"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
    
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
