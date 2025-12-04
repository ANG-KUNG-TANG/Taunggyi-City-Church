from typing import List, Optional, Dict, Any, Tuple
from django.db.models import Q
from asgiref.sync import sync_to_async 
from django.core.cache import cache 
from apps.tcc.models.users.users import User
from apps.tcc.usecase.entities.users_entity import UserEntity  
from apps.tcc.usecase.repo.base.base_repo import BaseRepository
from apps.core.db.decorators import with_db_error_handling, with_retry
from apps.core.cache.decorator import cached, cache_invalidate
import logging
import hashlib

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository[User, UserEntity]):
    """
    Pure data access layer for User model.
    No business logic, no authentication, no password handling.
    """
    
    def __init__(self):
        super().__init__(User)
    
    # ============ REQUIRED ABSTRACT METHOD ============
    
    async def _model_to_entity(self, user_model) -> UserEntity:
        """Convert Django model to UserEntity - REQUIRED by BaseRepository"""
        if user_model is None:
            return None
        return UserEntity.from_model(user_model)
    
    # ============ CORE CRUD WITH CACHING ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=["user:{user_entity.id}", "user:email:{user_entity.email}", "users:list:*"],
        namespace="users",
        version="1"
    )
    async def create(self, data: Dict, user=None, request=None) -> Optional[UserEntity]:
        """Create user - ONLY data persistence"""
        # NO password hashing here - use case handles that
        return await super().create(data, user, request)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(key_template="user:{object_id}", ttl=3600, namespace="users", version="1")
    async def get_by_id(self, object_id: int, user=None, *args, **kwargs) -> Optional[UserEntity]:
        """Get user by ID - with caching"""
        return await super().get_by_id(object_id, user, *args, **kwargs)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(key_template="user:email:{email}", ttl=3600, namespace="users", version="1")
    async def get_by_email(self, email: str, include_password_hash: bool = False) -> Optional[UserEntity]:
        """Get user by email - with caching (PURE data access)"""
        try:
            user = await sync_to_async(User.objects.get)(email=email, is_active=True)
            entity = await self._model_to_entity(user)
            if include_password_hash and hasattr(user, 'password'):
                entity.password_hash = user.password  # Just pass data, don't process
            return entity
        except User.DoesNotExist:
            logger.debug(f"User not found with email: {email}")
            return None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=["user:{object_id}", "user:email:{user_entity.email}", "users:list:*"],
        namespace="users",
        version="1"
    )
    async def update(self, object_id: int, data: Dict, user=None, request=None) -> Optional[UserEntity]:
        """Update user - with cache invalidation (PURE data update)"""
        # NO password hashing here - use case handles that
        return await super().update(object_id, data, user, request)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=["user:{object_id}", "user:email:{user.email}", "users:list:*"],
        namespace="users",
        version="1"
    )
    async def delete(self, object_id: int, user=None, request=None) -> bool:
        """Soft delete user - with cache invalidation"""
        return await super().delete(object_id, user, request)
    
    # ============ LIST OPERATIONS WITH CACHING ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def list_all(self, user=None, filters: Dict = None, **kwargs) -> List[UserEntity]:
        """List all users - without caching (bypass for fresh data)"""
        return await super().list_all(user, filters, **kwargs)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="users:list:{filters_hash}:{page}:{per_page}",
        ttl=900,  # 15 minutes for list views
        namespace="users",
        version="1"
    )
    async def get_paginated(self, filters: Dict = None, page: int = 1, per_page: int = 20) -> Tuple[List[UserEntity], int]:
        """Get paginated users - with caching (PURE data query)"""
        base_queryset = User.objects.filter(is_active=True)
        
        if filters:
            for key, value in filters.items():
                if value is not None:
                    base_queryset = base_queryset.filter(**{key: value})
        
        # Generate cache key
        filters_str = str(sorted(filters.items())) if filters else "all"
        filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:8]
        
        # Get total count
        total_count = await sync_to_async(base_queryset.count)()
        
        # Apply pagination
        offset = (page - 1) * per_page
        users_queryset = base_queryset.order_by('-created_at')[offset:offset + per_page]
        
        # Convert to entities
        users = []
        for user in await sync_to_async(list)(users_queryset):
            users.append(await self._model_to_entity(user))
            
        return users, total_count
    
    # ============ SPECIALIZED QUERIES ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def search_users(self, search_term: str, page: int = 1, per_page: int = 20) -> Tuple[List[UserEntity], int]:
        """Search users - no caching due to dynamic nature (PURE data query)"""
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
    @cached(key_template="user:exists:email:{email}", ttl=300, namespace="users", version="1")
    async def email_exists(self, email: str) -> bool:
        """Check if email exists - with caching (PURE data check)"""
        return await sync_to_async(User.objects.filter(email=email, is_active=True).exists)()
    
    # ============ BULK OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=["users:list:*", "user:exists:email:*"],
        namespace="users",
        version="1"
    )
    async def bulk_create(self, instances: List, user=None, request=None):
        """Bulk create users - with cache invalidation"""
        return await super().bulk_create(instances, user, request)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def save(self, instance, user=None, request=None):
        """Save user instance - with cache invalidation"""
        # Invalidate cache for this user
        if instance and instance.id:
            await self._invalidate_user_cache(instance.id, instance.email if hasattr(instance, 'email') else None)
        return await super().save(instance, user, request)
    
    # ============ CACHE UTILITY METHODS ============
    
    async def _invalidate_user_cache(self, user_id: int, email: str = None):
        """Helper to invalidate user cache (technical concern, not business)"""
        cache_keys = [f"user:{user_id}"]
        if email:
            cache_keys.append(f"user:email:{email}")
        
        for key in cache_keys:
            try:
                await sync_to_async(cache.delete)(key)
            except Exception as e:
                logger.warning(f"Failed to delete cache key {key}: {e}")