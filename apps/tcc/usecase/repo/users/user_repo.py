from typing import List, Optional, Dict, Any
from django.db.models import Q
from repo.base.modelrepo import DomainRepository
from apps.tcc.models.users.users import User
from apps.tcc.models.base.enums import UserRole, UserStatus
from models.base.permission import PermissionDenied
from entities.users import UserEntity
from core.db.decorators import with_db_error_handling, with_retry


class UserRepository(DomainRepository):
    
    def __init__(self):
        super().__init__(User)
    
    # ============ CRUD OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def create(self, user_entity: UserEntity, requesting_user: UserEntity) -> UserEntity:
        """Create new user - only admins can create users"""
        if not requesting_user.can_manage_users:
            raise PermissionDenied("Only administrators can create users")
        
        # Convert entity to model data
        user_data = self._entity_to_model_data(user_entity)
        
        # Create user model asynchronously
        user_model = await self.model_class.objects.acreate(**user_data)
        
        # Return as entity
        return await self._model_to_entity(user_model)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_id(self, id: int, requesting_user: UserEntity) -> Optional[UserEntity]:
        """Get user by ID with permission check"""
        try:
            user_model = await self.model_class.objects.aget(id=id, is_active=True)
            
            # Permission check
            if requesting_user.id != user_model.id and not requesting_user.can_manage_users:
                raise PermissionDenied("You can only view your own profile")
            
            return await self._model_to_entity(user_model)
        except User.DoesNotExist:
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_email(self, email: str, requesting_user: UserEntity) -> Optional[UserEntity]:
        """Get user by email with permission check"""
        try:
            user_model = await self.model_class.objects.aget(email=email, is_active=True)
            
            # Users can only see their own profile by email, admins can see all
            if requesting_user.email != email and not requesting_user.can_manage_users:
                raise PermissionDenied("You can only view your own profile")
            
            return await self._model_to_entity(user_model)
        except User.DoesNotExist:
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def update(self, id: int, user_entity: UserEntity, requesting_user: UserEntity) -> Optional[UserEntity]:
        """Update user - users can update their own profile, admins can update any"""
        target_user = await self.get_by_id(id, requesting_user)
        if not target_user:
            return None
        
        # Users can only update their own profile unless they're admins
        if requesting_user.id != target_user.id and not requesting_user.can_manage_users:
            raise PermissionDenied("You can only update your own profile")
        
        # Get update data (filter fields based on permissions)
        update_data = self._get_filtered_update_data(user_entity, requesting_user)
        
        # Update model asynchronously
        updated_count = await self.model_class.objects.filter(id=id).aupdate(**update_data)
        if updated_count:
            return await self.get_by_id(id, requesting_user)
        return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def delete(self, id: int, requesting_user: UserEntity) -> bool:
        """Soft delete user - only admins can delete users"""
        if not requesting_user.can_manage_users:
            raise PermissionDenied("Only administrators can delete users")
        
        # Soft delete (set is_active=False) asynchronously
        updated_count = await self.model_class.objects.filter(id=id).aupdate(is_active=False)
        return updated_count > 0
    
    # ============ SYSTEM REQUIREMENTS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_all(self, requesting_user: UserEntity, filters: Dict = None) -> List[UserEntity]:
        """Get all users with permission filtering"""
        if not requesting_user.can_manage_users:
            # Regular users only see their own profile
            return [requesting_user]
        
        queryset = User.objects.filter(is_active=True)
        
        if filters:
            queryset = queryset.filter(**filters)
        
        # Convert queryset to list asynchronously
        users = []
        async for user in queryset:
            users.append(await self._model_to_entity(user))
        return users
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_role(self, role: UserRole, requesting_user: UserEntity) -> List[UserEntity]:
        """Get users by role - admin only"""
        if not requesting_user.can_manage_users:
            raise PermissionDenied("Only administrators can filter users by role")
        
        users = []
        async for user in User.objects.filter(role=role, is_active=True):
            users.append(await self._model_to_entity(user))
        return users
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def search_users(self, search_term: str, requesting_user: UserEntity) -> List[UserEntity]:
        """Search users by name or email"""
        if not requesting_user.can_manage_users:
            # Regular users can only search for themselves
            if search_term.lower() in [requesting_user.name.lower(), requesting_user.email.lower()]:
                return [requesting_user]
            return []
        
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
    async def get_ministry_leaders(self, requesting_user: UserEntity) -> List[UserEntity]:
        """Get all ministry leaders"""
        return await self.get_by_role(UserRole.MINISTRY_LEADER, requesting_user)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def change_user_status(self, user_id: int, status: UserStatus, admin_user: UserEntity) -> Optional[UserEntity]:
        """Change user status - admin only"""
        if not admin_user.can_manage_users:
            raise PermissionDenied("Only administrators can change user status")
        
        user = await self.get_by_id(user_id, admin_user)
        if not user:
            return None
        
        # Update status asynchronously
        await self.model_class.objects.filter(id=user_id).aupdate(status=status)
        return await self.get_by_id(user_id, admin_user)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists (for validation)"""
        return await User.objects.filter(email=email, is_active=True).aexists()
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_active_users_count(self) -> int:
        """Get count of active users (for reporting)"""
        return await User.objects.filter(is_active=True).acount()
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_users_by_status(self, status: UserStatus, requesting_user: UserEntity) -> List[UserEntity]:
        """Get users by status - admin only"""
        if not requesting_user.can_manage_users:
            raise PermissionDenied("Only administrators can filter by status")
        
        users = []
        async for user in User.objects.filter(status=status, is_active=True):
            users.append(await self._model_to_entity(user))
        return users
    
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
    
    def _get_filtered_update_data(self, user_entity: UserEntity, requesting_user: UserEntity) -> Dict[str, Any]:
        """Get filtered update data based on user permissions"""
        update_data = self._entity_to_model_data(user_entity)
        
        # Non-admins cannot change role, status, or system fields
        if not requesting_user.can_manage_users:
            restricted_fields = ['role', 'status', 'is_staff', 'is_superuser']
            for field in restricted_fields:
                update_data.pop(field, None)
        
        return update_data