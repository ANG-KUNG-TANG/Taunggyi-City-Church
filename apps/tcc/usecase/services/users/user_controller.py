import logging
from typing import Dict, Any, Optional, List, Tuple
from functools import wraps

from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema, 
    UserUpdateInputSchema,
    UserQueryInputSchema,
    UserSearchInputSchema,
    EmailCheckInputSchema,

)

# Import decorators
from apps.core.schemas.validator.user_deco import (
    validate_user_create,
    validate_user_update,
    validate_user_query,
    validate_user_search,
    validate_email_check,
    require_admin,
    require_member,
    validate_user_ownership,
    validate_and_authorize_user_create,
    validate_and_authorize_user_update,
    validate_and_authorize_user_query
)

# Import dependency container
from apps.tcc.usecase.dependencies.user_dep import get_user_dependency_container

# FIXED: Use only UserExceptionHandler since it now converts to core exceptions
from apps.tcc.usecase.services.exceptions.u_handler_exceptions import handle_user_exceptions
from apps.tcc.usecase.entities.users_entity import UserEntity
from apps.tcc.usecase.domain_exception.auth_exceptions import AuthenticationException
from apps.core.cache.async_cache import AsyncCache
from apps.core.schemas.out_schemas.user_out_schemas import EmailCheckResponseSchema

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


class UserController:
    """
    User Controller - Returns domain entities ONLY (no APIResponse)
    NOTE: Does NOT inherit from BaseController to avoid duplicate exception handling
    """
    
    def __init__(self, cache: Optional[AsyncCache] = None):
        self._cache = cache
        self._dependency_container = None

    async def initialize(self):
        """Initialize dependency container"""
        try:
            # Get dependency container instance
            self._dependency_container = await get_user_dependency_container(cache=self._cache)
            logger.info("UserController initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize UserController: {e}", exc_info=True)
            # Raise a domain exception for initialization errors
            from apps.core.core_exceptions.domain import DomainException
            raise DomainException(
                message="Failed to initialize user controller",
                context={"error": str(e)}
            )

    async def _get_use_case(self, use_case_name: str):
        """Get use case from dependency container"""
        if not self._dependency_container:
            await self.initialize()
        
        # Map use case names to container methods
        use_case_map = {
            'create_user': self._dependency_container.get_create_user_uc,
            'create_admin_user': self._dependency_container.get_create_admin_user_uc,
            'get_user_by_id': self._dependency_container.get_user_by_id_uc,
            'get_user_by_email': self._dependency_container.get_user_by_email_uc,
            'get_all_users': self._dependency_container.get_all_users_uc,
            'get_users_by_role': self._dependency_container.get_users_by_role_uc,
            'search_users': self._dependency_container.get_search_users_uc,
            'check_email': self._dependency_container.get_check_email_uc,
            'update_user': self._dependency_container.get_update_user_uc,
            'change_user_status': self._dependency_container.get_change_user_status_uc,
            'delete_user': self._dependency_container.get_delete_user_uc,
            'bulk_delete_users': self._dependency_container.get_bulk_delete_users_uc,
            'register_user': self._dependency_container.get_register_user_uc,  
        }
        
        if use_case_name not in use_case_map:
            raise RuntimeError(f"Use case {use_case_name} not found")
        
        # Get use case from container
        use_case_getter = use_case_map[use_case_name]
        return await use_case_getter()

    
    @ensure_initialized
    async def create_user(
        self, 
        user_data: UserCreateInputSchema, 
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Create a new user account - Returns Entity"""
        logger.info(f"Creating user with data: {user_data.model_dump(exclude={'password', 'password_confirm'})}")
        create_user_uc = await self._get_use_case('create_user')
        
        # Add debug logging to see what's happening
        logger.debug(f"Input data: {user_data.model_dump(exclude={'password', 'password_confirm'})}")
        logger.debug(f"Current user: {current_user.id if current_user else 'None'}")
        logger.debug(f"Context: {context}")
        
        result = await create_user_uc.execute(user_data.model_dump(), current_user, context or {})
        logger.info(f"User created successfully: {result.id if hasattr(result, 'id') else 'No ID'}")
        return result
    
    @ensure_initialized
    async def register_user(
        self, 
        user_data: UserCreateInputSchema, 
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Public user registration - Returns Entity"""
        register_user_uc = await self._get_use_case('register_user')
        return await register_user_uc.execute(user_data.model_dump(), None, context or {})
    
    @require_admin
    @ensure_initialized
    async def create_admin_user(
        self, 
        user_data: UserCreateInputSchema, 
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Create admin user - Returns Entity"""
        create_admin_uc = await self._get_use_case('create_admin_user')
        return await create_admin_uc.execute(user_data.model_dump(), current_user, context or {})

    # ========== READ Operations ==========
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

    # @handle_user_exceptions
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

    # @handle_user_exceptions
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

    # @handle_user_exceptions
    # @validate_user_search
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

    # @handle_user_exceptions
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
    # @handle_user_exceptions
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

    # @handle_user_exceptions
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

    # @handle_user_exceptions
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

    
    
    # ========== EMAIL Operations ==========
    # @handle_user_exceptions
    @validate_email_check
    @ensure_initialized
    async def check_email_availability(
        self,
        validated_data: EmailCheckInputSchema,
        context: Dict[str, Any] = None
    ) -> EmailCheckResponseSchema:
        """Check if email exists - Returns EmailCheckResponseSchema"""
        check_email_uc = await self._get_use_case('check_email')
        input_data = {'email': validated_data.email}
        result = await check_email_uc.execute(input_data, None, context or {})
        return result

    # ========== DELETE Operations ==========
    # @handle_user_exceptions
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
        result = await delete_user_uc.execute(input_data, current_user, context or {})
        return result

    # @handle_user_exceptions
    @require_admin
    @ensure_initialized
    async def bulk_delete_users(
        self,
        user_ids: List[int],
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Bulk delete users - Returns result dict"""
        bulk_delete_uc = await self._get_use_case('bulk_delete_users')
        input_data = {'user_ids': user_ids}
        result = await bulk_delete_uc.execute(input_data, current_user, context or {})
        return result

    # ========== UTILITY Methods ==========
    # @handle_user_exceptions
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

    # @handle_user_exceptions
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

    async def get_all_use_cases(self) -> Dict[str, Any]:
        """Get all use cases from dependency container"""
        if not self._dependency_container:
            await self.initialize()
        
        return await self._dependency_container.get_all_user_use_cases()


# Factory functions
async def create_user_controller(cache: Optional[AsyncCache] = None) -> UserController:
    """Create user controller with cache"""
    controller = UserController(cache=cache)
    await controller.initialize()
    return controller


# Singleton instance (optional)
_singleton_controller: Optional[UserController] = None

async def get_user_controller(cache: Optional[AsyncCache] = None) -> UserController:
    """Get singleton instance of UserController"""
    global _singleton_controller
    if _singleton_controller is None:
        _singleton_controller = await create_user_controller(cache=cache)
    return _singleton_controller