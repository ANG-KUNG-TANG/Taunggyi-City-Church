from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from django.db import models
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from apps.tcc.models.base.base_model import BaseModel
from apps.tcc.utils.audit_logging import AuditLogger
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)
E = TypeVar('E')  # Entity type

class BaseRepository(Generic[T, E], ABC):
    """
    Unified base repository with common CRUD operations, permissions, audit, and soft delete
    """
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    # ============ CORE CRUD OPERATIONS ============
    
    @abstractmethod
    async def get_by_id(self, id: int, user=None, **kwargs) -> Optional[E]:
        pass
    
    @abstractmethod
    async def create(self, data: Dict, user=None, request=None) -> E:
        pass
    
    @abstractmethod
    async def update(self, id: int, data: Dict, user=None, request=None) -> Optional[E]:
        pass
    
    @abstractmethod
    async def delete(self, id: int, user=None, request=None) -> bool:
        pass
    
    @abstractmethod
    async def list_all(self, user=None, filters: Dict = None, **kwargs) -> List[E]:
        pass
    
    @abstractmethod
    async def save(self, instance: T, user=None, request=None) -> T:
        pass
    
    @abstractmethod
    async def bulk_create(self, instances: List[T], user=None, request=None) -> List[T]:
        pass
    
    # ============ PERMISSION METHODS ============
    
    def _check_permission(self, user, obj, action: str):
        """
        Check domain permissions for the given action
        """
        attr_check = f"check_can_{action}"
        attr_can = f"can_{action}"

        # Strong permission (raises inside model)
        if hasattr(obj, attr_check):
            getattr(obj, attr_check)(user)
            return

        # Soft permission returning bool
        if hasattr(obj, attr_can):
            if not getattr(obj, attr_can)(user):
                raise PermissionDenied(f"You are not allowed to {action} this resource.")

        # No permission attribute → allow by default
        return
    
    def _check_model_permission(self, user, action: str, **filters):
        """
        Check permissions at model level before operations
        """
        # Create a mock instance for permission checking if needed
        mock_instance = self.model_class()
        self._check_permission(user, mock_instance, action)
    
    # ============ AUDIT METHODS ============
    
    def _log_create(self, user, obj, ip="system", user_agent="system"):
        """Log creation event"""
        AuditLogger.log_create(user, obj, ip, user_agent)
    
    def _log_update(self, user, obj, changes: Dict, ip="system", user_agent="system"):
        """Log update event"""
        AuditLogger.log_update(user, obj, changes, ip, user_agent)
    
    def _log_delete(self, user, obj, ip="system", user_agent="system"):
        """Log deletion event"""
        AuditLogger.log_delete(user, obj, ip, user_agent)
    
    def _log_view(self, user, obj):
        """Log view event"""
        AuditLogger.log_view(user, obj)
    
    # ============ SOFT DELETE METHODS ============
    
    def _soft_delete(self, obj, user=None):
        """Soft delete object"""
        if hasattr(obj, "soft_delete"):
            obj.soft_delete(user=user)
        elif hasattr(obj, 'is_active'):
            obj.is_active = False
            obj.save()
        else:
            raise AttributeError(f"Model {self.model_class.__name__} doesn't support soft delete")
    
    def _hard_delete(self, obj):
        """Hard delete object"""
        obj.delete()
    
    # ============ UTILITY METHODS ============
    
    def _get_audit_context(self, request):
        """Extract audit context from request"""
        if not request:
            return {}, "system", "system"
        
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'system')
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
            ip = request.META.get('REMOTE_ADDR', 'system')
        return ip
    
    def _apply_filters(self, queryset, filters: Dict[str, Any]):
        """Apply filters to queryset"""
        if filters:
            for key, value in filters.items():
                if value is not None:
                    if isinstance(value, (list, tuple)):
                        queryset = queryset.filter(**{f"{key}__in": value})
                    else:
                        queryset = queryset.filter(**{key: value})
        return queryset
    
    async def exists(self, id: int) -> bool:
        """Check if entity exists"""
        try:
            from asgiref.sync import sync_to_async
            return await sync_to_async(self.model_class.objects.filter(id=id).exists)()
        except Exception as e:
            logger.error(f"Error checking existence for {self.model_class.__name__} {id}: {e}")
            return False