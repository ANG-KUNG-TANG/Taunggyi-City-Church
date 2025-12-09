from typing import List, Optional, Dict, Any, Tuple
from django.db.models import Q
from asgiref.sync import sync_to_async 
from django.core.cache import cache 
from apps.tcc.models.users.users import User
from apps.tcc.usecase.entities.users_entity import UserEntity  
from apps.tcc.usecase.repo.base.base_repo import BaseRepository
from apps.core.db.decorators import  with_db_error_handling, with_retry, circuit_breaker
from apps.core.cache.decorator import cached, cache_invalidate
import logging
import hashlib

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository[User, UserEntity]):
    """
    User-specific repository with full implementation
    Includes caching, retry, and error handling
    """
    
    def __init__(self):
        super().__init__(User)
        self.cache_prefix = "user"
    
    async def to_entity(self, model_instance):
        """Convert model to entity."""
        return await self._model_to_entity(model_instance)
    
    
    def _model_to_entity(self, user_model) -> UserEntity:
        """Convert model to entity - User-specific"""
        if user_model is None:
            return None
        return UserEntity.from_model(user_model)
    
    @circuit_breaker()
    @with_db_error_handling
    @with_retry(max_attempts=3)
    @cache_invalidate(
        key_templates=["user:{user_entity.id}", "user:email:{user_entity.email}", "users:list:*"],
        namespace="users",
        version="1"
    )
    async def create(self, data: Dict[str, Any], audit_context: Optional[Dict] = None) -> UserEntity:
        """Create a new user with audit context support."""
        try:
            # Get the model's field names
            model_fields = [f.name for f in self.model_class._meta.get_fields()]
            
            # Filter data to only include model fields
            filtered_data = {}
            skipped_fields =[]
            for key, value in data.items():
                if key in model_fields:
                    filtered_data[key] = value
                else:
                   skipped_fields.append(key)
            
            if skipped_fields:
                logger.debug(
                    f"Skipped fields for User model: {skipped_fields}",
                    extra={'skipped_count': len(skipped_fields)}
                )
            # Create the user model
            user_model = self.model_class(**filtered_data)
            
            # Save the user
            user_model.save()
            
            # Convert to entity and return - NO AWAIT if _model_to_entity is synchronous
            return self._model_to_entity(user_model)  # Remove the 'await'!
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}", exc_info=True)
            raise
        
    @with_db_error_handling
    @cached(ttl=300, key_template="user:{user_id}", namespace="users", version="1")
    async def get_by_id(self, user_id: int, user=None, **kwargs) -> Optional[UserEntity]:
        """Get user by ID with caching"""
        try:
            from asgiref.sync import sync_to_async
            # Get from database
            user_model = await sync_to_async(self.model_class.objects.filter(id=user_id).first)()
            # Convert to entity - NO AWAIT
            return self._model_to_entity(user_model)
            
        except Exception as e:
            logger.error(f"UserRepository.get_by_id failed: {str(e)}", exc_info=True)
            raise
    
    @with_db_error_handling
    @with_retry()
    @cached(key_template="user:email:{email}", ttl=3600, namespace="users", version="1")
    async def get_by_email(self, email: str, include_password_hash: bool = False) -> Optional[UserEntity]:
        """Get user by email - with caching (PURE data access)"""
        try:
            user = await sync_to_async(User.objects.get)(email=email, is_active=True)
            entity = self._model_to_entity(user)  # NO AWAIT
            if include_password_hash and hasattr(user, 'password'):
                entity.password_hash = user.password
            return entity
        except User.DoesNotExist:
            logger.debug(f"User not found with email: {email}")
            return None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            return None
    
    @with_db_error_handling
    @with_retry(max_attempts=3)
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
    @with_retry(max_attempts=3)
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
    @with_retry(max_attempts=3)
    async def list_all(self, user=None, filters: Dict = None, **kwargs) -> List[UserEntity]:
        """List all users - without caching (bypass for fresh data)"""
        return await super().list_all(user, filters, **kwargs)
    
    @with_db_error_handling
    @with_retry(max_attempts=3)
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
    @with_retry(max_attempts=3)
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
    @with_retry(max_attempts=3)
    @cached(key_template="user:exists:email:{email}", ttl=300, namespace="users", version="1")
    async def email_exists(self, email: str) -> bool:
        """Check if email exists - with caching (PURE data check)"""
        return await sync_to_async(User.objects.filter(email=email, is_active=True).exists)()
    
    # ============ BULK OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_attempts=3)
    @cache_invalidate(
        key_templates=["users:list:*", "user:exists:email:*"],
        namespace="users",
        version="1"
    )
    async def bulk_create(self, instances: List, user=None, request=None):
        """Bulk create users - with cache invalidation"""
        return await super().bulk_create(instances, user, request)
    
    @with_db_error_handling
    @with_retry(max_attempts=3)
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