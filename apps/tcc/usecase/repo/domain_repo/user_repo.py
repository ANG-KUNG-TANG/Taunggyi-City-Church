from typing import List, Optional, Dict, Any
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
    @cache_invalidate(
        key_templates=[
            "user:{id}",
            "user:email:{user_entity.email}",
            "users:list:*"
        ],
        namespace="users",
        version="1"
    )
    async def create(self, user_entity: UserEntity) -> UserEntity:
        """Create new user with audit logging and cache invalidation"""
        # Convert entity to model data
        user_data = self._entity_to_model_data(user_entity)
        
        # Create user model asynchronously
        user_model = await self.model_class.objects.acreate(**user_data)
        user_entity_result = await self._model_to_entity(user_model)
        
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
        ttl=3600,  # 1 hour
        namespace="users",
        version="1"
    )
    async def get_by_id(self, id: int) -> Optional[UserEntity]:
        """Get user by ID with caching"""
        try:
            user_model = await self.model_class.objects.aget(id=id, is_active=True)
            return await self._model_to_entity(user_model)
        except User.DoesNotExist:
            logger.debug(f"User not found with ID: {id}")
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="user:email:{email}",
        ttl=3600,  # 1 hour
        namespace="users",
        version="1"
    )
    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        """Get user by email with caching"""
        try:
            user_model = await self.model_class.objects.aget(email=email, is_active=True)
            return await self._model_to_entity(user_model)
        except User.DoesNotExist:
            logger.debug(f"User not found with email: {email}")
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=[
            "user:{id}",
            "user:email:{user_entity.email}",
            "user:email:{old_email}",  # This will be formatted in the method
            "users:list:*"
        ],
        namespace="users",
        version="1"
    )
    async def update(self, id: int, user_entity: UserEntity) -> Optional[UserEntity]:
        """Update user with audit logging and cache invalidation"""
        target_user = await self._get_by_id_uncached(id)
        if not target_user:
            return None
        
        # Store old email for cache invalidation
        old_email = target_user.email
        
        # Get update data
        update_data = self._entity_to_model_data(user_entity)
        
        # Update model asynchronously
        updated_count = await self.model_class.objects.filter(id=id).aupdate(**update_data)
        if updated_count:
            updated_user = await self._get_by_id_uncached(id)
            
            # Audit logging
            changes = {
                'email': {'old': old_email, 'new': updated_user.email},
                'name': {'old': target_user.name, 'new': updated_user.name}
            }
            await AuditLogger.log_update(
                user=None,
                obj=updated_user,
                changes=changes,
                notes=f"Updated user: {updated_user.email}",
                ip_address="system",
                user_agent="system"
            )
            
            # Add old_email to the instance for decorator formatting
            setattr(self, 'old_email', old_email)
            
            logger.info(f"User updated successfully: {updated_user.email}")
            return updated_user
        return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
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
        """Soft delete user with audit logging and cache invalidation"""
        target_user = await self._get_by_id_uncached(id)
        if not target_user:
            return False
        
        # Store target_user for decorator
        setattr(self, 'target_user', target_user)
        
        # Soft delete (set is_active=False) asynchronously
        updated_count = await self.model_class.objects.filter(id=id).aupdate(is_active=False)
        
        if updated_count:
            # Audit logging
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
    
    # ============ QUERY OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="users:list:{filters_hash}",
        ttl=1800,  # 30 minutes
        namespace="users",
        version="1"
    )
    async def get_all(self, filters: Dict = None) -> List[UserEntity]:
        """Get all users with caching"""
        queryset = User.objects.filter(is_active=True)
        
        if filters:
            for key, value in filters.items():
                queryset = queryset.filter(**{key: value})
        
        # Add filters_hash for decorator key formatting
        filters_hash = hash(str(filters)) if filters else "all"
        setattr(self, 'filters_hash', filters_hash)
        
        # Convert queryset to list asynchronously
        users = []
        async for user in queryset:
            users.append(await self._model_to_entity(user))
        return users
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="users:role:{role}",
        ttl=3600,  # 1 hour
        namespace="users",
        version="1"
    )
    async def get_by_role(self, role: UserRole) -> List[UserEntity]:
        """Get users by role with caching"""
        users = []
        async for user in User.objects.filter(role=role, is_active=True):
            users.append(await self._model_to_entity(user))
        return users
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="users:search:{search_term}",
        ttl=900,  # 15 minutes
        namespace="users",
        version="1"
    )
    async def search_users(self, search_term: str) -> List[UserEntity]:
        """Search users by name or email with caching"""
        queryset = User.objects.filter(
            Q(is_active=True) &
            (Q(name__icontains=search_term) | Q(email__icontains=search_term))
        )
        
        users = []
        async for user in queryset:
            users.append(await self._model_to_entity(user))
        return users
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return await User.objects.filter(email=email, is_active=True).aexists()
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="users:count:active",
        ttl=300,  # 5 minutes
        namespace="users",
        version="1"
    )
    async def get_active_users_count(self) -> int:
        """Get count of active users with caching"""
        return await User.objects.filter(is_active=True).acount()
    
    # ============ BATCH OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=["users:list:*"],
        namespace="users",
        version="1"
    )
    async def bulk_create(self, user_entities: List[UserEntity]) -> List[UserEntity]:
        """Bulk create users with audit logging and cache invalidation"""
        user_data_list = [self._entity_to_model_data(user_entity) for user_entity in user_entities]
        
        created_users = []
        for user_data in user_data_list:
            user_model = await self.model_class.objects.acreate(**user_data)
            user_entity = await self._model_to_entity(user_model)
            created_users.append(user_entity)
            
            # Audit logging for each user
            await AuditLogger.log_create(
                user=None,
                obj=user_model,
                notes=f"Bulk created user: {user_entity.email}",
                ip_address="system",
                user_agent="system"
            )
        
        logger.info(f"Bulk created {len(created_users)} users")
        return created_users
    
    # ============ INTERNAL METHODS ============
    
    async def _get_by_id_uncached(self, id: int) -> Optional[UserEntity]:
        """Internal method to get user by ID without cache (for update operations)"""
        try:
            user_model = await self.model_class.objects.aget(id=id, is_active=True)
            return await self._model_to_entity(user_model)
        except User.DoesNotExist:
            return None
    
    # ============ CONVERSION METHODS ============
    
    async def _model_to_entity(self, user_model: User) -> UserEntity:
        """Convert Django model to UserEntity"""
        return UserEntity(
            id=user_model.id,
            name=user_model.name,
            email=user_model.email,
            phone_number=user_model.phone_number,
            age=user_model.age,
            gender=user_model.gender,
            marital_status=user_model.marital_status,
            date_of_birth=user_model.date_of_birth,
            testimony=user_model.testimony,
            baptism_date=user_model.baptism_date,
            membership_date=user_model.membership_date,
            role=user_model.role,
            status=user_model.status,
            is_staff=user_model.is_staff,
            is_superuser=user_model.is_superuser,
            is_active=user_model.is_active,
            email_notifications=user_model.email_notifications,
            sms_notifications=user_model.sms_notifications,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at
        )
    
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