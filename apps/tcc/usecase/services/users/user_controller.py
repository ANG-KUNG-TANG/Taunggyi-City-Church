import logging
from typing import Dict, Any, Optional, List, Tuple
from functools import wraps

from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema, 
    UserUpdateInputSchema,
    UserQueryInputSchema,
    UserSearchInputSchema,
    EmailCheckInputSchema,
    UserChangePasswordInputSchema,
)

# Import decorators
from apps.core.schemas.validator.user_deco import (
    validate_user_create,
    validate_user_update,
    validate_user_query,
    validate_user_search,
    validate_change_password,
    validate_email_check,
    require_admin,
    require_member,
    validate_user_ownership,
    validate_and_authorize_user_create,
    validate_and_authorize_user_update,
    validate_and_authorize_user_query
)

# Import dependency container
from apps.tcc.usecase.dependencies.user_dep import UserDependencyContainer, get_user_dependency_container

from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.tcc.usecase.services.exceptions.u_handler_exceptions import UserExceptionHandler
from apps.tcc.usecase.entities.users_entity import UserEntity
from apps.tcc.usecase.domain_exception.auth_exceptions import AuthenticationException
from apps.core.cache.async_cache import AsyncCache

logger = logging.getLogger(__name__)


def ensure_initialized(func):
    """
    Decorator to ensure controller is initialized before method execution
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self._dependency_container:
            await self.initialize()
        return await func(self, *args, **kwargs)
    return wrapper


class UserController(BaseController):
    """
    User Controller - Returns domain entities ONLY (no APIResponse)
    """
    
    def __init__(self, cache: Optional[AsyncCache] = None):
        self._cache = cache
        self._dependency_container: Optional[UserDependencyContainer] = None

    async def initialize(self):
        """Initialize dependency container"""
        try:
            # Create a new dependency container instance
            self._dependency_container = UserDependencyContainer(cache=self._cache)
            logger.info("UserController initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize UserController: {e}")
            raise

    async def _get_use_case(self, use_case_name: str):
        """Get use case from dependency container"""
        if not self._dependency_container:
            await self.initialize()
        
        # Map use case names to container methods
        use_case_map = {
            'create_user': self._dependency_container.get_create_user_uc,
            'get_user_by_id': self._dependency_container.get_user_by_id_uc,
            'get_user_by_email': self._dependency_container.get_user_by_email_uc,
            'get_all_users': self._dependency_container.get_all_users_uc,
            'get_users_by_role': self._dependency_container.get_users_by_role_uc,
            'search_users': self._dependency_container.get_search_users_uc,
            'update_user': self._dependency_container.get_update_user_uc,
            'change_user_status': self._dependency_container.get_change_user_status_uc,
            'delete_user': self._dependency_container.get_delete_user_uc,
        }
        
        if use_case_name not in use_case_map:
            raise RuntimeError(f"Use case {use_case_name} not found")
        
        # Get use case from container
        use_case_getter = use_case_map[use_case_name]
        return await use_case_getter()

    # ========== CREATE Operations ==========
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_and_authorize_user_create
    @ensure_initialized
    async def create_user(
        self, 
        user_data: UserCreateInputSchema, 
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Create a new user account - Returns Entity"""
        create_user_uc = await self._get_use_case('create_user')
        return await create_user_uc.execute(user_data.model_dump(), None, context or {})

    # ========== READ Operations ==========
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_member
    @ensure_initialized
    async def get_user_by_id(
        self, 
        user_id: int,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Get user by ID - Returns Entity"""
        get_user_by_id_uc = await self._get_use_case('get_user_by_id')
        input_data = {'user_id': user_id}
        return await get_user_by_id_uc.execute(input_data, current_user, context or {})

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_member
    @ensure_initialized
    async def get_user_by_email(
        self, 
        email: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Get user by email - Returns Entity"""
        get_user_by_email_uc = await self._get_use_case('get_user_by_email')
        input_data = {'email': email}
        return await get_user_by_email_uc.execute(input_data, current_user, context or {})

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_and_authorize_user_query
    @ensure_initialized
    async def get_all_users(
        self,
        validated_data: UserQueryInputSchema,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> Tuple[List[UserEntity], int]:
        """Get all users with pagination - Returns (Entities, total_count)"""
        get_all_users_uc = await self._get_use_case('get_all_users')
        input_data = validated_data.model_dump()
        return await get_all_users_uc.execute(input_data, current_user, context or {})

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_admin
    @ensure_initialized
    async def get_users_by_role(
        self,
        role: str,
        page: int = 1,
        per_page: int = 20,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> Tuple[List[UserEntity], int]:
        """Get users by role with pagination - Returns (Entities, total_count)"""
        get_users_by_role_uc = await self._get_use_case('get_users_by_role')
        input_data = {'role': role, 'page': page, 'per_page': per_page}
        return await get_users_by_role_uc.execute(input_data, current_user, context or {})

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_user_search
    @require_admin
    @ensure_initialized
    async def search_users(
        self,
        validated_data: UserSearchInputSchema,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> Tuple[List[UserEntity], int]:
        """Search users with filters - Returns (Entities, total_count)"""
        search_users_uc = await self._get_use_case('search_users')
        input_data = validated_data.model_dump()
        return await search_users_uc.execute(input_data, current_user, context or {})

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_member
    @ensure_initialized
    async def get_current_user_profile(
        self,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Get current user's profile - Returns Entity"""
        if not current_user or not hasattr(current_user, 'id'):
            raise AuthenticationException("User authentication required")
        
        return await self.get_user_by_id(current_user.id, current_user, context)

    # ========== UPDATE Operations ==========
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_and_authorize_user_update
    @ensure_initialized
    async def update_user(
        self,
        user_id: int,
        user_data: UserUpdateInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Update user by ID - Returns Entity"""
        update_user_uc = await self._get_use_case('update_user')
        input_data = {
            'user_id': user_id,
            'update_data': user_data.model_dump(exclude_unset=True)
        }
        return await update_user_uc.execute(input_data, current_user, context or {})

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_user_update
    @validate_user_ownership()
    @ensure_initialized
    async def update_current_user_profile(
        self,
        user_data: UserUpdateInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Update current user profile - Returns Entity"""
        if not current_user or not hasattr(current_user, 'id'):
            raise AuthenticationException("User authentication required")
        
        return await self.update_user(current_user.id, user_data, current_user, context)

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_admin
    @ensure_initialized
    async def change_user_status(
        self,
        user_id: int,
        status: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Change user status (active/inactive) - Returns Entity"""
        change_user_status_uc = await self._get_use_case('change_user_status')
        input_data = {'user_id': user_id, 'status': status}
        return await change_user_status_uc.execute(input_data, current_user, context or {})

    # ========== PASSWORD Operations ==========
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_change_password
    @require_member
    @ensure_initialized
    async def change_password(
        self,
        validated_data: UserChangePasswordInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Change current user's password - Returns Entity"""
        update_user_uc = await self._get_use_case('update_user')
        input_data = {
            'user_id': current_user.id,
            'update_data': {'password': validated_data.new_password}
        }
        return await update_user_uc.execute(input_data, current_user, context or {})

    # ========== EMAIL Operations ==========
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_email_check
    @ensure_initialized
    async def check_email_availability(
        self,
        validated_data: EmailCheckInputSchema,
        context: Dict[str, Any] = None
    ) -> bool:
        """Check if email is available - Returns boolean"""
        get_user_by_email_uc = await self._get_use_case('get_user_by_email')
        try:
            input_data = {'email': validated_data.email}
            await get_user_by_email_uc.execute(input_data, None, context or {})
            return False  # Email exists
        except Exception:
            return True  # Email is available

    # ========== DELETE Operations ==========
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_admin
    @ensure_initialized
    async def delete_user(
        self,
        user_id: int,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> bool:
        """Delete user by ID - Returns boolean success"""
        delete_user_uc = await self._get_use_case('delete_user')
        input_data = {'user_id': user_id}
        return await delete_user_uc.execute(input_data, current_user, context or {})

    # ========== UTILITY Methods ==========
    async def execute_direct_use_case(
        self,
        use_case_name: str,
        input_data: Dict[str, Any],
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> Any:
        """
        Directly execute a use case without additional decorators
        Useful for testing or direct operations
        """
        use_case = await self._get_use_case(use_case_name)
        return await use_case.execute(input_data, current_user, context or {})

    async def batch_operation(
        self,
        use_case_name: str,
        items: List[Dict[str, Any]],
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> List[Any]:
        """
        Execute batch operations using a specific use case
        """
        results = []
        use_case = await self._get_use_case(use_case_name)
        
        for item in items:
            try:
                result = await use_case.execute(item, current_user, context or {})
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process item {item}: {e}")
                results.append(None)
        
        return results


# Alternative factory functions
async def create_user_controller_with_cache(cache: AsyncCache) -> UserController:
    """Create user controller with specific cache instance"""
    controller = UserController(cache=cache)
    await controller.initialize()
    return controller


async def create_user_controller_default() -> UserController:
    """Create user controller with default settings"""
    controller = UserController()
    await controller.initialize()
    return controller


# Singleton instance (optional)
_singleton_controller: Optional[UserController] = None

async def get_singleton_user_controller() -> UserController:
    """Get singleton instance of UserController"""
    global _singleton_controller
    if _singleton_controller is None:
        _singleton_controller = await create_user_controller_default()
    return _singleton_controller