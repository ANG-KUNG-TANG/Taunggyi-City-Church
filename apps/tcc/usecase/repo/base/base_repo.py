from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import models
from django.db.models import Q

from apps.tcc.models.base.base import BaseModel
from apps.tcc.utils.audit_logging import AuditLogger
from apps.tcc.models.base.enums import UserRole

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T], ABC):
    """
    Abstract base repository with common CRUD operations
    """
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    @abstractmethod
    def get_by_id(self, id: int, user) -> Optional[T]:
        pass
    
    @abstractmethod
    def get_all(self, user, filters: Dict = None) -> List[T]:
        pass
    
    @abstractmethod
    def create(self, data: Dict, user, request=None) -> T:
        pass
    
    @abstractmethod
    def update(self, id: int, data: Dict, user, request=None) -> Optional[T]:
        pass
    
    @abstractmethod
    def delete(self, id: int, user, request=None) -> bool:
        pass
    
    @abstractmethod
    def filter(self, user, **filters) -> List[T]:
        pass
    
    def _get_audit_context(self, request):
        """Extract audit context from request"""
        if not request:
            return {}, "", ""
        
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        context = {
            'ip_address': ip_address,
            'user_agent': user_agent,
            'request_path': request.path,
            'request_method': request.method,
        }
        return context, ip_address, user_agent
    
    def _get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class ModelRepository(BaseRepository[T]):
    """
    Concrete repository implementation for Django models
    """
    
    def get_by_id(self, id: int, user) -> Optional[T]:
        """
        Get object by ID with permission check
        """
        try:
            obj = self.model_class.objects.get(id=id, is_active=True)
            if hasattr(obj, 'check_can_view'):
                obj.check_can_view(user)
            elif hasattr(obj, 'can_view') and not obj.can_view(user):
                raise PermissionDenied("You don't have permission to view this resource")
            
            # Log view action for sensitive data
            if self._is_sensitive_model():
                AuditLogger.log_view(user, obj)
            
            return obj
        except self.model_class.DoesNotExist:
            return None
    
    def get_all(self, user, filters: Dict = None) -> List[T]:
        """
        Get all objects with permission filtering
        """
        queryset = self.model_class.objects.filter(is_active=True)
        
        # Apply filters
        if filters:
            queryset = queryset.filter(**filters)
        
        # Filter based on user permissions
        if hasattr(self.model_class, 'can_view'):
            # This is a simplified approach - in practice, you might need more complex filtering
            objects = []
            for obj in queryset:
                try:
                    if obj.can_view(user):
                        objects.append(obj)
                except PermissionDenied:
                    continue
            return objects
        else:
            return list(queryset)
    
    def create(self, data: Dict, user, request=None) -> T:
        """
        Create new object with permission check and audit logging
        """
        # Check create permission
        if hasattr(self.model_class, 'check_can_create'):
            self.model_class.check_can_create(user)
        elif hasattr(self.model_class, 'can_create') and not self.model_class.can_create(user):
            raise PermissionDenied("You don't have permission to create this resource")
        
        # Prepare data with user context
        create_data = data.copy()
        if 'created_by' not in create_data:
            create_data['created_by'] = user
        
        # Create object
        obj = self.model_class(**create_data)
        
        # Get audit context
        context, ip_address, user_agent = self._get_audit_context(request)
        
        # Save with audit
        if hasattr(obj, 'save_with_audit'):
            obj.save_with_audit(user, request)
        else:
            obj.save()
            AuditLogger.log_create(user, obj, ip_address, user_agent)
        
        return obj
    
    def update(self, id: int, data: Dict, user, request=None) -> Optional[T]:
        """
        Update existing object with permission check and audit logging
        """
        obj = self.get_by_id(id, user)
        if not obj:
            return None
        
        # Check edit permission
        if hasattr(obj, 'check_can_edit'):
            obj.check_can_edit(user)
        elif hasattr(obj, 'can_edit') and not obj.can_edit(user):
            raise PermissionDenied("You don't have permission to edit this resource")
        
        # Update fields
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        
        # Get audit context
        context, ip_address, user_agent = self._get_audit_context(request)
        
        # Track changes for audit (simplified)
        changes = {field: {'old': getattr(obj, field), 'new': value} for field, value in data.items()}
        
        # Save with audit
        if hasattr(obj, 'save_with_audit'):
            obj.save_with_audit(user, request)
        else:
            obj.save()
            AuditLogger.log_update(user, obj, changes, ip_address, user_agent)
        
        return obj
    
    def delete(self, id: int, user, request=None) -> bool:
        """
        Soft delete object with permission check and audit logging
        """
        obj = self.get_by_id(id, user)
        if not obj:
            return False
        
        # Check delete permission
        if hasattr(obj, 'check_can_delete'):
            obj.check_can_delete(user)
        elif hasattr(obj, 'can_delete') and not obj.can_delete(user):
            raise PermissionDenied("You don't have permission to delete this resource")
        
        # Get audit context
        context, ip_address, user_agent = self._get_audit_context(request)
        
        # Delete with audit
        if hasattr(obj, 'delete_with_audit'):
            obj.delete_with_audit(user, request)
        else:
            AuditLogger.log_delete(user, obj, ip_address, user_agent)
            obj.soft_delete(user=user)
        
        return True
    
    def filter(self, user, **filters) -> List[T]:
        """
        Filter objects with permission checking
        """
        queryset = self.model_class.objects.filter(is_active=True, **filters)
        
        # Apply permission filtering
        if hasattr(self.model_class, 'can_view'):
            objects = []
            for obj in queryset:
                try:
                    if obj.can_view(user):
                        objects.append(obj)
                except PermissionDenied:
                    continue
            return objects
        else:
            return list(queryset)
    
    def _is_sensitive_model(self):
        """Check if model contains sensitive data"""
        sensitive_models = ['User', 'Donation', 'PrayerRequest']
        return self.model_class.__name__ in sensitive_models