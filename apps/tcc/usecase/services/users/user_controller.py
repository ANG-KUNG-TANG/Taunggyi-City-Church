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
from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.core.schemas.validator.user_deco import (
    # Validation decorators
    validate_user_create,
    validate_user_update,
    validate_user_query,
    validate_user_search,
    validate_email_check,
    
    # AuthZ decorators
    public_endpoint,
    require_authenticated,
    require_admin,
    require_ownership,
    authenticated_with_ownership,
    admin_or_owner,
)

from apps.tcc.usecase.dependencies.user_dep import get_user_dependency_container
from apps.tcc.usecase.entities.users_entity import UserEntity
from apps.tcc.usecase.domain_exception.auth_exceptions import AuthenticationException
from apps.core.cache.async_cache import AsyncCache
from apps.core.schemas.out_schemas.user_out_schemas import EmailCheckResponseSchema

logger = logging.getLogger(__name__)


def ensure_initialized(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self._dependency_container:
            await self.initialize()
        return await func(self, *args, **kwargs)
    return wrapper


class UserController(BaseController):
    def __init__(self, cache: Optional[AsyncCache] = None):
        self._cache = cache
        self._dependency_container = None

    async def initialize(self):
        try:
            self._dependency_container = await get_user_dependency_container(cache=self._cache)
            logger.info("UserController initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize UserController: {e}", exc_info=True)
            from apps.core.core_exceptions.domain import DomainException
            raise DomainException(
                message="Failed to initialize user controller",
                context={"error": str(e)}
            )

    async def _get_use_case(self, use_case_name: str):
        if not self._dependency_container:
            await self.initialize()
        
        use_case_map = {
            # CREATE
            'create_user': self._dependency_container.get_create_user_uc,
            'create_admin_user': self._dependency_container.get_create_admin_user_uc,
            'register_user': self._dependency_container.get_register_user_uc,
            
            # READ
            'get_user_by_id': self._dependency_container.get_user_by_id_uc,
            'get_user_by_email': self._dependency_container.get_user_by_email_uc,
            'get_all_users': self._dependency_container.get_all_users_uc,
            'get_users_by_role': self._dependency_container.get_users_by_role_uc,
            'search_users': self._dependency_container.get_search_users_uc,
            'check_email': self._dependency_container.get_check_email_uc,
            
            # UPDATE
            'update_user': self._dependency_container.get_update_user_uc,
            'change_user_status': self._dependency_container.get_change_user_status_uc,
            
            # DELETE
            'delete_user': self._dependency_container.get_delete_user_uc,
            'bulk_delete_users': self._dependency_container.get_bulk_delete_users_uc,
        }
        
        if use_case_name not in use_case_map:
            raise ValueError(f"Unknown use case: {use_case_name}")
        
        use_case_getter = use_case_map[use_case_name]
        return await use_case_getter()
    
    # ========== CREATE Operations ==========
    
    @public_endpoint
    @validate_user_create
    @ensure_initialized
    async def register_user(
        self, 
        user_data: UserCreateInputSchema, 
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """
        PUBLIC user registration
        NOTE: NO current_user parameter for public registration
        """
        logger.info(f"Registering user: {user_data.email}")
        use_case = await self._get_use_case('create_user')
        
        result = await use_case.execute(
            input_data=user_data.model_dump(),  
            context=context or {}
        )
        
        logger.info(f"User registered: {result.id}")
        return result
    
    @require_admin
    @validate_user_create
    @ensure_initialized
    async def create_admin_user(
        self, 
        user_data: UserCreateInputSchema, 
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """
        Admin-only: Create admin user
        NOTE: current_user is passed for auditing purposes
        """
        logger.info(f"Admin creating user: {user_data.email}")
        use_case = await self._get_use_case('create_admin_user')
        
        # For admin creation, pass context with current_user info
        execution_context = context or {}
        execution_context['current_user_id'] = current_user.id if hasattr(current_user, 'id') else None
        execution_context['current_user_email'] = getattr(current_user, 'email', None)
        
        # FIXED: Pass data as input_data parameter
        return await use_case.execute(
            input_data=user_data.model_dump(),  # CHANGED: user_data -> input_data
            user=current_user,  # Pass current_user as user parameter
            context=execution_context
        )

    # ========== READ Operations ==========
    
    @require_authenticated
    @ensure_initialized
    async def get_current_user_profile(
        self,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Get current user's profile"""
        if not current_user or not hasattr(current_user, 'id'):
            raise AuthenticationException("User authentication required")
        
        get_user_by_id_uc = await self._get_use_case('get_user_by_id')
        
        # Pass user_id in input_data
        return await get_user_by_id_uc.execute(
            input_data={'user_id': current_user.id},  # CHANGED: Use input_data
            user=current_user,
            context=context
        )
    
    @admin_or_owner('user_id', 'id')
    @ensure_initialized
    async def get_user_by_id(
        self, 
        user_id: int,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Get user by ID (admins can view any, users can only view themselves)"""
        get_user_by_id_uc = await self._get_use_case('get_user_by_id')
        
        # FIXED: Pass user_id in input_data
        return await get_user_by_id_uc.execute(
            input_data={'user_id': user_id},  # CHANGED: Pass in input_data
            user=current_user,
            context=context
        )
    
    @require_admin
    @ensure_initialized
    async def get_user_by_email(
        self, 
        email: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Admin-only: Get user by email"""
        get_user_by_email_uc = await self._get_use_case('get_user_by_email')
        
        # FIXED: Pass email in input_data
        return await get_user_by_email_uc.execute(
            input_data={'email': email},  # CHANGED: Pass in input_data
            user=current_user,
            context=context
        )
    
    @require_authenticated
    @validate_user_query
    @ensure_initialized
    async def get_all_users(
        self,
        validated_data: UserQueryInputSchema,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> Tuple[List[UserEntity], int]:
        """Get all users with pagination"""
        get_all_users_uc = await self._get_use_case('get_all_users')
        
        # FIXED: Pass filters in input_data
        return await get_all_users_uc.execute(
            input_data=validated_data.model_dump(),  # CHANGED: filters -> input_data
            user=current_user,
            context=context
        )
    
    # ========== UPDATE Operations ==========
    
    @authenticated_with_ownership('user_id', 'id')
    @validate_user_update
    @ensure_initialized
    async def update_user(
        self,
        user_id: int,
        user_data: UserUpdateInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Update user by ID (users can update their own, admins can update any)"""
        update_user_uc = await self._get_use_case('update_user')
        
        # FIXED: Pass both user_id and update_data in input_data
        return await update_user_uc.execute(
            input_data={
                'user_id': user_id,
                'update_data': user_data.model_dump(exclude_unset=True)
            },  # CHANGED: Pass in input_data
            user=current_user,
            context=context
        )
    
    @require_authenticated
    @validate_user_update
    @ensure_initialized
    async def update_current_user_profile(
        self,
        user_data: UserUpdateInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Update current user profile"""
        if not current_user or not hasattr(current_user, 'id'):
            raise AuthenticationException("User authentication required")
        
        # Use the update_user method with current user's ID
        return await self.update_user(
            user_id=current_user.id,
            user_data=user_data,
            current_user=current_user,
            context=context
        )
    
    @require_admin
    @ensure_initialized
    async def change_user_status(
        self,
        user_id: int,
        status: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserEntity:
        """Change user status (admin only)"""
        change_user_status_uc = await self._get_use_case('change_user_status')
        
        # FIXED: Pass user_id and status in input_data
        return await change_user_status_uc.execute(
            input_data={'user_id': user_id, 'status': status},  # CHANGED: Pass in input_data
            user=current_user,
            context=context
        )

    # ========== EMAIL Operations ==========
    
    @public_endpoint
    @validate_email_check
    @ensure_initialized
    async def check_email_availability(
        self,
        validated_data: EmailCheckInputSchema,
        context: Dict[str, Any] = None
    ) -> EmailCheckResponseSchema:
        """Check if email exists (public endpoint)"""
        check_email_uc = await self._get_use_case('check_email')
        
        # FIXED: Pass email in input_data
        return await check_email_uc.execute(
            input_data={'email': validated_data.email},  # CHANGED: Pass in input_data
            context=context or {}
        )

    # ========== DELETE Operations ==========
    
    @require_admin
    @ensure_initialized
    async def delete_user(
        self,
        user_id: int,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> bool:
        """Delete user by ID (admin only)"""
        delete_user_uc = await self._get_use_case('delete_user')
        
        # FIXED: Pass user_id in input_data
        return await delete_user_uc.execute(
            input_data={'user_id': user_id},  # CHANGED: Pass in input_data
            user=current_user,
            context=context
        )
    
    # ========== OTHER Methods ==========
    
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
        """Get users by role"""
        get_users_by_role_uc = await self._get_use_case('get_users_by_role')
        
        # FIXED: Pass parameters in input_data
        return await get_users_by_role_uc.execute(
            input_data={'role': role, 'page': page, 'per_page': per_page},
            user=current_user,
            context=context
        )
    
    @require_admin
    @validate_user_search
    @ensure_initialized
    async def search_users(
        self,
        validated_data: UserSearchInputSchema,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> Tuple[List[UserEntity], int]:
        """Search users"""
        search_users_uc = await self._get_use_case('search_users')
        
        # FIXED: Pass search data in input_data
        return await search_users_uc.execute(
            input_data=validated_data.model_dump(),
            user=current_user,
            context=context
        )
    
    # ========== UTILITY Methods ==========
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Health check endpoint
        """
        try:
            # Test basic operations
            from django.db import connection
            from asgiref.sync import sync_to_async
            
            def sync_check_db():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return cursor.fetchone()
            
            await sync_to_async(sync_check_db, thread_sensitive=False)()
            
            return {
                'status': 'healthy',
                'service': 'UserController',
                'database': 'connected',
                'cache_enabled': self._cache is not None,
                'initialized': self._dependency_container is not None
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'service': 'UserController'
            }


# Factory functions
async def create_user_controller(cache: Optional[AsyncCache] = None) -> UserController:
    """Create user controller with cache"""
    controller = UserController(cache=cache)
    await controller.initialize()
    return controller


# Singleton instance
_singleton_controller: Optional[UserController] = None

async def get_user_controller(cache: Optional[AsyncCache] = None) -> UserController:
    """Get singleton instance of UserController"""
    global _singleton_controller
    if _singleton_controller is None:
        _singleton_controller = await create_user_controller(cache=cache)
    return _singleton_controller
