from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from django.db import models
from django.db.models import Q
from apps.tcc.models.base.base_model import BaseModel
from apps.tcc.utils.audit_logging import AuditLogger

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
