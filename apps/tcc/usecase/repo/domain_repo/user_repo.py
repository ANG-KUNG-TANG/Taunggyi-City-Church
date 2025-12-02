from typing import List, Optional, Dict, Any, Tuple
from django.db.models import Q
from asgiref.sync import sync_to_async 
from apps.core.cache.async_cache import AsyncCache
from apps.tcc.models.users.users import User
from apps.tcc.models.base.enums import UserRole, UserStatus
from apps.tcc.usecase.entities.users import UserEntity  
from apps.tcc.usecase.repo.base.modelrepo import DomainRepository
from apps.core.db.decorators import with_db_error_handling, with_retry
from apps.core.cache.decorator import cached, cache_invalidate
import logging

logger = logging.getLogger(__name__)

class UserRepository(DomainRepository):
    
    def __init__(self, cache: AsyncCache = None):
        super().__init__(User)
        self.cache = cache
    
    # ============ OVERRIDDEN CRUD OPERATIONS WITH CACHING ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=["user:{user_entity.id}", "user:email:{user_entity.email}", "users:list:*"],
        namespace="users",
        version="1"
    )
    async def create(self, data, user=None, request=None) -> UserEntity:
        """Create user with password handling"""
        try:
            logger.info(f"UserRepository.create called with data type: {type(data)}")
            
            # Handle both dict and entity input
            if hasattr(data, '__dict__'):
                # It's an entity - convert to dict
                user_data = {k: v for k, v in data.__dict__.items() 
                           if not k.startswith('_') and v is not None}
            else:
                # It's a dict - use copy
                user_data = data.copy() if isinstance(data, dict) else data
            
            # Extract password if provided
            password = user_data.pop('password', None)
            
            # Create user via parent
            user_entity = await super().create(user_data, user, request)
            
            # Set password if provided
            if password:
                user_model = await sync_to_async(User.objects.get)(id=user_entity.id)
                user_model.set_password(password)
                await sync_to_async(user_model.save)()
            
            logger.info(f"User created successfully: {user_entity.email}")
            return user_entity
            
        except Exception as e:
            logger.error(f"Error in user creation: {str(e)}", exc_info=True)
            raise
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(key_template="user:{object_id}", ttl=3600, namespace="users", version="1")
    async def get_by_id(self, object_id, user=None, *args, **kwargs) -> Optional[UserEntity]:
        return await super().get_by_id(object_id, user, *args, **kwargs)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(key_template="user:email:{email}", ttl=3600, namespace="users", version="1")
    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        """Get user by email with caching"""
        try:
            user = await sync_to_async(User.objects.get)(email=email, is_active=True)
            return await self._model_to_entity(user)
        except User.DoesNotExist:
            logger.debug(f"User not found with email: {email}")
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=["user:{object_id}", "user:email:{user_entity.email}", "users:list:*"],
        namespace="users",
        version="1"
    )
    async def update(self, object_id, data, user=None, request=None) -> Optional[UserEntity]:
        """Update user with proper change tracking"""
        # Use parent's update which already handles audit logging
        return await super().update(object_id, data, user, request)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=["user:{object_id}", "user:email:{user.email}", "users:list:*"],
        namespace="users",
        version="1"
    )
    async def delete(self, object_id, user=None, request=None) -> bool:
        """Soft delete user"""
        return await super().delete(object_id, user, request)
    
    # ============ BUSINESS OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="users:list:{filters_hash}:{page}:{per_page}",
        ttl=900,
        namespace="users",
        version="1"
    )
    async def get_paginated_users(self, filters: Dict = None, page: int = 1, per_page: int = 20) -> Tuple[List[UserEntity], int]:
        """Get paginated users with filters"""
        base_queryset = User.objects.filter(is_active=True)
        
        if filters:
            for key, value in filters.items():
                base_queryset = base_queryset.filter(**{key: value})
        
        # Add filters_hash for decorator
        filters_hash = hash(str(filters)) if filters else "all"
        setattr(self, 'filters_hash', filters_hash)
        setattr(self, 'page', page)
        setattr(self, 'per_page', per_page)
        
        # Get total count
        total_count = await sync_to_async(base_queryset.count)()
        
        # Calculate offset and apply pagination
        offset = (page - 1) * per_page
        users_queryset = base_queryset.order_by('-created_at')[offset:offset + per_page]
        
        users = []
        for user in await sync_to_async(list)(users_queryset):
            users.append(await self._model_to_entity(user))
            
        return users, total_count
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def search_users(self, search_term: str, page: int = 1, per_page: int = 20) -> Tuple[List[UserEntity], int]:
        """Search users by name or email"""
        queryset = User.objects.filter(
            Q(is_active=True) &
            (Q(name__icontains=search_term) | Q(email__icontains=search_term))
        )
        
        total_count = await sync_to_async(queryset.count)()
        offset = (page - 1) * per_page
        
        users_queryset = queryset.order_by('-created_at')[offset:offset + per_page]
        users = []
        for user in await sync_to_async(list)(users_queryset):
            users.append(await self._model_to_entity(user))
            
        return users, total_count
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return await sync_to_async(User.objects.filter(email=email, is_active=True).exists)()
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def verify_password(self, user_id: int, password: str) -> bool:
        """Verify user password"""
        try:
            user = await sync_to_async(User.objects.get)(id=user_id, is_active=True)
            return user.check_password(password)
        except User.DoesNotExist:
            return False

    # ============ CONVERSION METHODS ============
    
    async def _model_to_entity(self, user_model) -> UserEntity:
        """Convert Django model to UserEntity"""
        return UserEntity.from_model(user_model)