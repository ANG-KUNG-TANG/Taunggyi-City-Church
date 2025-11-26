from datetime import timezone
from typing import List, Optional, Dict, Any, Tuple
from django.db import transaction
from django.db.models import Q
from apps.core.cache.async_cache import AsyncCache
from repo.base.modelrepo import DomainRepository
from apps.tcc.models.users.users import User
from apps.tcc.models.base.enums import UserRole, UserStatus
from entities.users import UserEntity
from core.db.decorators import with_db_error_handling, with_retry
from utils.audit_logging import AuditLogger
from core.cache.decorator import cached, cache_invalidate
import logging

logger = logging.getLogger(__name__)

class UserRepository(DomainRepository):
    
    def __init__(self, cache: AsyncCache = None):
        super().__init__(User)
        self.cache = cache
    
    # ============ CRUD OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @transaction.atomic
    @cache_invalidate(
        key_templates=[
            "user:{id}",
            "user:email:{user_entity.email}",
            "users:list:*"
        ],
        namespace="users",
        version="1"
    )
    async def create(self, user_entity: UserEntity, password: str = None) -> UserEntity:
        """Create new user with password handling"""
        user_entity.prepare_for_persistence()
        
        # Convert entity to model data
        user_data = self._entity_to_model_data(user_entity)
        
        # Create user model
        user_model = await self.model_class.objects.acreate(**user_data)
        
        # Set password if provided
        if password:
            user_model.set_password(password)
            await user_model.asave(update_fields=['password'])
        
        user_entity_result = UserEntity.from_model(user_model)
        
        # Audit logging
        await AuditLogger.log_create(
            user=None,
            obj=user_model,
            notes=f"Created user: {user_entity_result.email}",
            ip_address="system",
            user_agent="system"
        )
        
        logger.info(f"User created successfully: {user_entity_result.email}")
        return user_entity_result
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="user:{id}",
        ttl=3600,
        namespace="users",
        version="1"
    )
    async def get_by_id(self, id: int) -> Optional[UserEntity]:
        """Get user by ID with caching"""
        try:
            user_model = await self.model_class.objects.aget(id=id, is_active=True)
            return UserEntity.from_model(user_model)
        except User.DoesNotExist:
            logger.debug(f"User not found with ID: {id}")
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="user:email:{email}",
        ttl=3600,
        namespace="users",
        version="1"
    )
    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        """Get user by email with caching"""
        try:
            user_model = await self.model_class.objects.aget(email=email, is_active=True)
            return UserEntity.from_model(user_model)
        except User.DoesNotExist:
            logger.debug(f"User not found with email: {email}")
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @transaction.atomic
    @cache_invalidate(
        key_templates=[
            "user:{id}",
            "user:email:{user_entity.email}",
            "users:list:*"
        ],
        namespace="users",
        version="1"
    )
    async def update(self, id: int, user_entity: UserEntity) -> Optional[UserEntity]:
        """Update user with proper change tracking"""
        target_user = await self._get_by_id_uncached(id)
        if not target_user:
            return None
        
        user_entity.prepare_for_persistence()
        
        # Get update data
        update_data = self._entity_to_model_data(user_entity)
        
        # Update model
        updated_count = await self.model_class.objects.filter(id=id).aupdate(**update_data)
        if updated_count:
            updated_user = await self._get_by_id_uncached(id)
            
            # Audit logging
            changes = self._get_changes(target_user, updated_user)
            await AuditLogger.log_update(
                user=None,
                obj=updated_user,
                changes=changes,
                notes=f"Updated user: {updated_user.email}",
                ip_address="system",
                user_agent="system"
            )
            
            logger.info(f"User updated successfully: {updated_user.email}")
            return updated_user
        return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @transaction.atomic
    @cache_invalidate(
        key_templates=[
            "user:{id}",
            "user:email:{target_user.email}",
            "users:list:*"
        ],
        namespace="users",
        version="1"
    )
    async def delete(self, id: int) -> bool:
        """Soft delete user"""
        target_user = await self._get_by_id_uncached(id)
        if not target_user:
            return False
        
        # Soft delete
        updated_count = await self.model_class.objects.filter(id=id).aupdate(is_active=False)
        
        if updated_count:
            await AuditLogger.log_delete(
                user=None,
                obj=target_user,
                notes=f"Deleted user: {target_user.email}",
                ip_address="system",
                user_agent="system"
            )
            
            logger.info(f"User deleted successfully: {target_user.email}")
            return True
        
        return False

    # ============ BUSINESS OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_paginated_users(self, filters: Dict = None, page: int = 1, per_page: int = 20) -> Tuple[List[UserEntity], int]:
        """Get paginated users with filters"""
        queryset = User.objects.filter(is_active=True)
        
        if filters:
            for key, value in filters.items():
                if value is not None:
                    queryset = queryset.filter(**{key: value})
        
        # Get total count
        total_count = await queryset.acount()
        
        # Calculate offset and apply pagination
        offset = (page - 1) * per_page
        paginated_queryset = queryset[offset:offset + per_page]
        
        # Convert to entities
        users = []
        async for user in paginated_queryset:
            users.append(UserEntity.from_model(user))
            
        return users, total_count
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def search_users(self, search_term: str, page: int = 1, per_page: int = 20) -> Tuple[List[UserEntity], int]:
        """Search users by name or email"""
        queryset = User.objects.filter(
            Q(is_active=True) &
            (Q(name__icontains=search_term) | Q(email__icontains=search_term))
        )
        
        total_count = await queryset.acount()
        offset = (page - 1) * per_page
        paginated_queryset = queryset[offset:offset + per_page]
        
        users = []
        async for user in paginated_queryset:
            users.append(UserEntity.from_model(user))
            
        return users, total_count
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return await User.objects.filter(email=email, is_active=True).aexists()
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def verify_password(self, user_id: int, password: str) -> bool:
        """Verify user password"""
        try:
            user = await User.objects.aget(id=user_id, is_active=True)
            return user.check_password(password)
        except User.DoesNotExist:
            return False

    # ============ INTERNAL METHODS ============
    
    async def _get_by_id_uncached(self, id: int) -> Optional[UserEntity]:
        """Internal method to get user by ID without cache"""
        try:
            user_model = await self.model_class.objects.aget(id=id, is_active=True)
            return UserEntity.from_model(user_model)
        except User.DoesNotExist:
            return None
    
    def _entity_to_model_data(self, user_entity: UserEntity) -> Dict[str, Any]:
        """Convert UserEntity to model data dictionary"""
        return {
            'name': user_entity.name,
            'email': user_entity.email,
            'phone_number': user_entity.phone_number,
            'age': user_entity.age,
            'gender': user_entity.gender,
            'marital_status': user_entity.marital_status,
            'date_of_birth': user_entity.date_of_birth,
            'testimony': user_entity.testimony,
            'baptism_date': user_entity.baptism_date,
            'membership_date': user_entity.membership_date,
            'role': user_entity.role,
            'status': user_entity.status,
            'is_staff': user_entity.is_staff,
            'is_superuser': user_entity.is_superuser,
            'is_active': user_entity.is_active,
            'email_notifications': user_entity.email_notifications,
            'sms_notifications': user_entity.sms_notifications,
        }
    
    def _get_changes(self, old_entity: UserEntity, new_entity: UserEntity) -> Dict:
        """Track changes between entity versions"""
        changes = {}
        fields_to_track = ['name', 'email', 'role', 'status']
        
        for field in fields_to_track:
            old_value = getattr(old_entity, field, None)
            new_value = getattr(new_entity, field, None)
            if old_value != new_value:
                changes[field] = {'old': old_value, 'new': new_value}
        
        return changes