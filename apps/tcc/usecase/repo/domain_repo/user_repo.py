import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from django.db import IntegrityError
from django.db.models import Q
from asgiref.sync import sync_to_async 
from django.core.cache import cache
from pydantic import ValidationError
from apps.core.core_exceptions.domain import DomainValidationException
from apps.tcc.models.users.users import User
from apps.tcc.usecase.domain_exception.u_exceptions import UserAlreadyExistsException
from apps.tcc.usecase.entities.users_entity import UserEntity  
from apps.tcc.usecase.repo.base.base_repo import BaseRepository
from apps.core.db.decorators import with_db_error_handling, with_retry, circuit_breaker
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
    
    async def to_entity(self, user_model, include_password_hash=False):
        """Convert Django User model to domain entity"""
        try:
            # Ensure all required fields are extracted
            entity_data = UserEntity()
            
            # Add roles/role information
            if hasattr(user_model, 'roles'):
                entity_data['roles'] = await self._extract_roles(user_model)
            elif hasattr(user_model, 'role'):
                entity_data['role'] = user_model.role
                entity_data['roles'] = [user_model.role]
            
            # Add password hash if needed
            if include_password_hash:
                entity_data['password_hash'] = user_model.password
            
            # Create entity (adjust based on your UserEntity class)
            return UserEntity(**entity_data)
        
        except Exception as e:
            logger.error(f"Error converting user model to entity: {e}", exc_info=True)
            raise
    
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
    async def create(self, data: Dict[str, Any], audit_context=None):
        def sync_create():
            try:
                user = self.model_class(**data)
                user.full_clean()
                user.save()
                return user
            except ValidationError as e:
                logger.debug(f"Django ValidationError: {e.message_dict}")
                # Check if it's an email uniqueness error
                if "email" in e.message_dict and any("already exists" in str(msg).lower() for msg in e.message_dict['email']):
                    raise UserAlreadyExistsException(email=data.get("email"))
                # For other validation errors
                raise DomainValidationException(
                    message="Invalid user data",
                    field_errors=e.message_dict
                )
            except IntegrityError as e:
                logger.debug(f"IntegrityError: {str(e)}")
                # Check if it's a unique constraint violation on email
                if "email" in str(e).lower() or "unique" in str(e).lower():
                    raise UserAlreadyExistsException(email=data.get("email"))
                raise

        try:
            user_model = await sync_to_async(sync_create, thread_sensitive=False)()
            return self._model_to_entity(user_model)
        except UserAlreadyExistsException:
            raise 
        except Exception as e:
            logger.error(f"Unexpected error in user creation: {e}", exc_info=True)
            raise
        
    @with_db_error_handling
    @cached(ttl=300, key_template="user:{user_id}", namespace="users", version="1")
    async def get_by_id(self, user_id: int, user=None, **kwargs) -> Optional[UserEntity]:
        """Get user by ID with caching"""
        try:
            def sync_get_by_id():
                return self.model_class.objects.filter(id=user_id).first()
            
            user_model = await sync_to_async(sync_get_by_id, thread_sensitive=True)()
            return self._model_to_entity(user_model)
            
        except Exception as e:
            logger.error(f"UserRepository.get_by_id failed: {str(e)}", exc_info=True)
            raise
    
    @with_db_error_handling
    @with_retry()
    @cached(key_template="user:email:{email}", ttl=3600, namespace="users", version="1")
    async def get_by_email(self, email: str, include_password_hash: bool = False):
        """Get user by email with thread safety fix"""
        try:
            logger.debug(f"Searching for user with email: {email}")
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            # Use case-insensitive search
            def sync_get():
                return User.objects.filter(email__iexact=email).first()
            
            # Get the Django user model
            user = await asyncio.to_thread(sync_get)
            
            if not user:
                logger.warning(f"No user found for email: {email}")
                return None
            
            logger.debug(f"Found user: {user.email} (ID: {user.id})")
            
            # Convert to entity - NOTE: to_entity is async, so we need to await it
            entity = self._model_to_entity(user)
            
            # Add password hash if requested
            if include_password_hash:
                # Create a copy with password_hash attribute
                from dataclasses import replace
                # If UserEntity is a dataclass, use replace
                if hasattr(entity, '__dataclass_fields__'):
                    entity = replace(entity, password_hash=user.password)
                else:
                    # Otherwise, set as attribute
                    entity.password_hash = user.password
            
            return entity
            
        except Exception as e:
            logger.error(f"Error in get_by_email for {email}: {e}", exc_info=True)
            raise
        
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
        try:
            # Define synchronous functions for database operations
            def sync_get_queryset():
                base_queryset = User.objects.filter(is_active=True)
                
                if filters:
                    for key, value in filters.items():
                        if value is not None:
                            base_queryset = base_queryset.filter(**{key: value})
                return base_queryset
            
            def sync_get_count(queryset):
                return queryset.count()
            
            def sync_get_users(queryset, offset, limit):
                return list(queryset.order_by('-created_at')[offset:offset + limit])
            
            # Get queryset
            base_queryset = await sync_to_async(sync_get_queryset, thread_sensitive=True)()
            
            # Get total count
            total_count = await sync_to_async(sync_get_count, thread_sensitive=True)(base_queryset)
            
            # Apply pagination
            offset = (page - 1) * per_page
            users_list = await sync_to_async(sync_get_users, thread_sensitive=True)(base_queryset, offset, per_page)
            
            # Convert to entities
            users = []
            for user in users_list:
                users.append(self._model_to_entity(user))
                
            return users, total_count
            
        except Exception as e:
            logger.error(f"Error in get_paginated: {str(e)}", exc_info=True)
            return [], 0
    
    # ============ SPECIALIZED QUERIES ============
    
    @with_db_error_handling
    @with_retry(max_attempts=3)
    async def search_users(self, search_term: str, page: int = 1, per_page: int = 20) -> Tuple[List[UserEntity], int]:
        """Search users - no caching due to dynamic nature (PURE data query)"""
        try:
            # Define synchronous functions
            def sync_search():
                return User.objects.filter(
                    Q(is_active=True) &
                    (Q(name__icontains=search_term) | Q(email__icontains=search_term))
                )
            
            def sync_get_count(queryset):
                return queryset.count()
            
            def sync_get_users(queryset, offset, limit):
                return list(queryset.order_by('-created_at')[offset:offset + limit])
            
            # Get queryset
            queryset = await sync_to_async(sync_search, thread_sensitive=True)()
            
            # Get total count
            total_count = await sync_to_async(sync_get_count, thread_sensitive=True)(queryset)
            
            # Apply pagination
            offset = (page - 1) * per_page
            users_list = await sync_to_async(sync_get_users, thread_sensitive=True)(queryset, offset, per_page)
            
            # Convert to entities
            users = []
            for user in users_list:
                users.append(self._model_to_entity(user))
                
            return users, total_count
            
        except Exception as e:
            logger.error(f"Error in search_users: {str(e)}", exc_info=True)
            return [], 0
    
    @with_db_error_handling
    @with_retry(max_attempts=3)
    @cached(key_template="user:exists:email:{email}", ttl=300, namespace="users", version="1")
    async def email_exists(self, email: str) -> bool:
        """Check if email exists - with caching (PURE data check)"""
        def sync_check():
            return User.objects.filter(email=email, is_active=True).exists()
        
        return await sync_to_async(sync_check, thread_sensitive=True)()
    
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
                await sync_to_async(cache.delete, thread_sensitive=False)(key)
            except Exception as e:
                logger.warning(f"Failed to delete cache key {key}: {e}")