from typing import List, Optional, Dict, Any
from django.db.models import Q
from repo.base.base_repo import ModelRepository
from apps.tcc.models.users.users import User
from apps.tcc.models.base.enums import UserRole, UserStatus
from models.base.permission import PermissionDenied




class UserRepository(ModelRepository[User]):
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_id(self, id: int, user) -> Optional[User]:
        """
        Get user by ID with permission check
        Regular users can only see their own profile, admins can see all
        """
        try:
            obj = self.model_class.objects.get(id=id, is_active=True)
            
            # Permission check
            if user.id != obj.id and not user.can_manage_users:
                raise PermissionDenied("You can only view your own profile")
            
            return obj
        except User.DoesNotExist:
            return None
    
    def get_by_email(self, email: str, user) -> Optional[User]:
        """
        Get user by email with permission check
        """
        try:
            obj = self.model_class.objects.get(email=email, is_active=True)
            
            # Users can only see their own profile by email, admins can see all
            if user.email != email and not user.can_manage_users:
                raise PermissionDenied("You can only view your own profile")
            
            return obj
        except User.DoesNotExist:
            return None
    
    def get_all(self, user, filters: Dict = None) -> List[User]:
        """
        Get all users with permission filtering
        Regular users can only see themselves, admins can see all
        """
        if not user.can_manage_users:
            # Regular users only see their own profile
            return [user]
        
        queryset = User.objects.filter(is_active=True)
        
        if filters:
            queryset = queryset.filter(**filters)
        
        return list(queryset)
    
    def create(self, data: Dict, user, request=None) -> User:
        """
        Create new user - only admins can create users
        """
        if not user.can_manage_users:
            raise PermissionDenied("Only administrators can create users")
        
        return super().create(data, user, request)
    
    def update(self, id: int, data: Dict, user, request=None) -> Optional[User]:
        """
        Update user - users can update their own profile, admins can update any
        """
        target_user = self.get_by_id(id, user)
        if not target_user:
            return None
        
        # Users can only update their own profile unless they're admins
        if user.id != target_user.id and not user.can_manage_users:
            raise PermissionDenied("You can only update your own profile")
        
        # Non-admins cannot change role or status
        if not user.can_manage_users:
            if 'role' in data:
                del data['role']
            if 'status' in data:
                del data['status']
            if 'is_staff' in data:
                del data['is_staff']
            if 'is_superuser' in data:
                del data['is_superuser']
        
        return super().update(id, data, user, request)
    
    def delete(self, id: int, user, request=None) -> bool:
        """
        Delete user - only admins can delete users
        """
        if not user.can_manage_users:
            raise PermissionDenied("Only administrators can delete users")
        
        return super().delete(id, user, request)
    
    def get_by_role(self, role: UserRole, user) -> List[User]:
        """Get users by role"""
        if not user.can_manage_users:
            raise PermissionDenied("Only administrators can filter users by role")
        
        return self.filter(user, role=role)
    
    def search_users(self, search_term: str, user) -> List[User]:
        """Search users by name or email"""
        if not user.can_manage_users:
            # Regular users can only search for themselves
            if search_term.lower() in [user.name.lower(), user.email.lower()]:
                return [user]
            return []
        
        queryset = User.objects.filter(
            Q(is_active=True) &
            (Q(name__icontains=search_term) | Q(email__icontains=search_term))
        )
        return list(queryset)
    
    def get_ministry_leaders(self, user) -> List[User]:
        """Get all ministry leaders"""
        return self.get_by_role(UserRole.MINISTRY_LEADER, user)
    
    def change_user_status(self, user_id: int, status: UserStatus, admin_user, request=None) -> Optional[User]:
        """Change user status - admin only"""
        if not admin_user.can_manage_users:
            raise PermissionDenied("Only administrators can change user status")
        
        user = self.get_by_id(user_id, admin_user)
        if not user:
            return None
        
        return self.update(user_id, {'status': status}, admin_user, request)