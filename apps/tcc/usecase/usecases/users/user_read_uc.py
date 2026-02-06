from typing import Dict, Any, List, Tuple
import uuid
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
        
        # Convert to integer for repository
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise DomainValidationException("Invalid User ID format. Must be an integer.")
        
        # Business rule: Users can only view their own profile unless they have permission
        if not await self._can_view_user(user, user_id):
            raise DomainValidationException(
                f"Insufficient permissions to view this user (ID: {user_id})",
                user_message="You do not have permission to view this user."
            )
        
        # Get user from repository
        user_entity = await self.user_repository.get_by_id(user_id, user=user)
        
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
            
        # Get current user ID - handle different possible attribute names
        current_user_id = None
        
        # Try to get user ID from various possible attributes
        if hasattr(current_user, 'id'):
            current_user_id = current_user.id
        elif hasattr(current_user, 'user_id'):
            current_user_id = current_user.user_id
        elif hasattr(current_user, 'get_id') and callable(current_user.get_id):
            current_user_id = current_user.get_id()
        
        # Convert current_user_id to string for comparison
        current_user_id_str = str(current_user_id) if current_user_id is not None else None
        target_user_id_str = str(target_user_id)
        
        # User can always view their own profile
        if current_user_id_str == target_user_id_str:
            return True
        
        # ================================================
        # FIX: Check for super_admin/admin permissions
        # ================================================
        
        # Method 1: Check for is_superuser or is_admin flag
        if hasattr(current_user, 'is_superuser') and current_user.is_superuser:
            return True
        
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            return True
        
        # Method 2: Check role names
        if hasattr(current_user, 'role'):
            role = str(current_user.role).lower()
            if role in ['super_admin', 'admin', 'superadmin', 'administrator']:
                return True
        
        # Method 3: Check for specific permissions
        if hasattr(current_user, 'has_permission') and callable(current_user.has_permission):
            # Check for any permission that indicates admin access
            permissions_to_check = ['can_view_users', 'can_view_all_users', 'admin_access', 'super_admin']
            for permission in permissions_to_check:
                if current_user.has_permission(permission):
                    return True
        
        # Method 4: Check for role object (if role is an object with permissions)
        if hasattr(current_user, 'role') and hasattr(current_user.role, 'is_admin'):
            if current_user.role.is_admin:
                return True
        
        # Method 5: Check if current_user has permissions attribute
        if hasattr(current_user, 'permissions'):
            permissions_list = getattr(current_user, 'permissions', [])
            if isinstance(permissions_list, list):
                if 'admin' in permissions_list or 'super_admin' in permissions_list:
                    return True
        
        # Default to False for safety
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
        
        # Get user from repository
        user_entity = await self.user_repository.get_by_email(email_input.email, user=user)
        
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
                email=user_entity.email,  
                is_active=user_entity.is_active,
                role=user_entity.role,
                first_name=getattr(user_entity, 'first_name', ''),
                last_name=getattr(user_entity, 'last_name', ''),
                # Hide other sensitive fields
                created_at=getattr(user_entity, 'created_at', None),
                updated_at=getattr(user_entity, 'updated_at', None)
            )
            return safe_entity
        
        return user_entity
    
    async def _can_view_sensitive_info(self, current_user, target_user_id: int) -> bool:
        """Business rule: Check if user can view sensitive user info"""
        if not current_user:
            return False
            
        # Get current user ID - handle different possible attribute names
        current_user_id = None
        
        if hasattr(current_user, 'id'):
            current_user_id = current_user.id
        elif hasattr(current_user, 'user_id'):
            current_user_id = current_user.user_id
        elif hasattr(current_user, 'get_id') and callable(current_user.get_id):
            current_user_id = current_user.get_id()
        
        # If we can't determine current user ID, check for superuser status
        if current_user_id is None:
            if hasattr(current_user, 'is_superuser') and current_user.is_superuser:
                return True
            return False
        
        # Convert IDs to strings for comparison
        current_user_id_str = str(current_user_id)
        target_user_id_str = str(target_user_id)
        
        # User can view their own sensitive info
        if current_user_id_str == target_user_id_str:
            return True
            
        # Admins can view sensitive info
        if hasattr(current_user, 'is_superuser') and current_user.is_superuser:
            return True
            
        return False


class ListUsersUseCase(BaseUseCase):
    """Get all users with pagination - Returns paginated result dict"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
        logger.info(f"ListUsersUseCase initialized")
    
    def _setup_configuration(self):
        logger.info(f"ListUsersUseCase._setup_configuration called")
        self.config.require_authentication = True
        self.config.required_permissions = ['can_view_users']
        self.config.validate_input = True
        logger.info(f"Config set: require_authentication={self.config.require_authentication}, required_permissions={self.config.required_permissions}")

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Dict[str, Any]:
        """Get all users - Returns paginated result dict"""
        logger.info(f"=== ListUsersUseCase._on_execute START ===")
        logger.info(f"Current user: {user}")
        logger.info(f"Current user type: {type(user)}")
        logger.info(f"Current user attributes: {dir(user) if hasattr(user, '__dir__') else 'No attributes'}")
        
        if user:
            logger.info(f"User ID: {getattr(user, 'id', 'No ID')}")
            logger.info(f"User email: {getattr(user, 'email', 'No email')}")
            logger.info(f"User is_superuser: {getattr(user, 'is_superuser', 'No is_superuser attr')}")
            logger.info(f"User is_staff: {getattr(user, 'is_staff', 'No is_staff attr')}")
            
            # Check permissions
            if hasattr(user, 'has_perm') and callable(user.has_perm):
                logger.info(f"User has_perm('can_view_users'): {user.has_perm('can_view_users')}")
            if hasattr(user, 'has_permission') and callable(user.has_permission):
                logger.info(f"User has_permission('can_view_users'): {user.has_permission('can_view_users')}")
        
        query_input = UserQueryInputSchema(**input_data)
        logger.info(f"Query input: {query_input}")
        
        # Apply business rules to filters
        filters = query_input.model_dump(exclude={'page', 'per_page', 'sort_by', 'sort_order'})
        logger.info(f"Initial filters: {filters}")
        
        # Business rule: Non-admins can only see active users
        if not (hasattr(user, 'is_superuser') and user.is_superuser):
            filters['is_active'] = True
            logger.info("Added is_active=True filter (non-admin user)")
        else:
            logger.info("Admin user - no is_active filter")
        
        logger.info(f"Final filters: {filters}")
        logger.info(f"Calling repository.get_paginated with page={query_input.page}, page_size={query_input.per_page}")
        
        # Get paginated results from repository
        result = await self.user_repository.get_paginated(
            filters=filters,
            page=query_input.page,
            page_size=query_input.per_page,
            sort_by=query_input.sort_by,
            include_inactive=False
        )
        
        logger.info(f"Repository returned result: {result}")
        if isinstance(result, dict) and 'pagination' in result:
            logger.info(f"Total users from repository: {result.get('pagination', {}).get('total', 0)}")
            logger.info(f"Items count: {len(result.get('items', []))}")
        
        logger.info(f"=== ListUsersUseCase._on_execute END ===")
        return result

class GetUsersByRoleUseCase(BaseUseCase):
    """Get users by role with pagination - Returns paginated result dict"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_view_users']
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Dict[str, Any]:
        """Get users by role - Returns paginated result dict"""
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
        result = await self.user_repository.get_paginated(
            filters=filters,
            page=page,
            page_size=per_page,  # Map per_page to page_size
            include_inactive=False
        )
        
        return result


class SearchUsersUseCase(BaseUseCase):
    """Search users - Returns paginated result dict"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_view_users']
        self.config.validate_input = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Dict[str, Any]:
        """Search users - Returns paginated result dict"""
        search_input = UserSearchInputSchema(**input_data)
        
        # Search using repository's search method which returns dict
        result = await self.user_repository.search(
            search_term=search_input.search_term,
            page=search_input.page,
            page_size=search_input.per_page,  # Map per_page to page_size
            filters={'is_active': True}  # Only active users by default
        )
        
        return result


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