from typing import Type, List, Optional, Dict, Any, TypeVar
from django.db import models
from asgiref.sync import sync_to_async
from .base_repo import BaseRepository
import logging

logger = logging.getLogger(__name__)

E = TypeVar('E')

class DomainRepository(BaseRepository):
    """Concrete implementation of BaseRepository for domain models"""
    
    def __init__(self, model_class: Type[models.Model]):
        super().__init__(model_class)
    
    # ============ SYNC CORE METHODS (for sync_to_async) ============
    
    def _get_by_id_sync(self, id: int, user=None, **kwargs):
        """Sync version of get_by_id"""
        self._check_model_permission(user, 'view')
        return self.model_class.objects.filter(id=id).first()
    
    def _create_sync(self, data: Dict, user=None, request=None):
        """Sync version of create"""
        self._check_model_permission(user, 'create')
        instance = self.model_class(**data)
        instance.save()
        
        # Audit logging
        ip, ua = "system", "system"
        if request:
            _, ip, ua = self._get_audit_context(request)
        self._log_create(user, instance, ip, ua)
        
        return instance
    
    def _update_sync(self, id: int, data: Dict, user=None, request=None):
        """Sync version of update"""
        instance = self._get_by_id_sync(id, user)
        if not instance:
            return None
        
        self._check_permission(user, instance, 'update')
        
        # Track changes
        changes = {}
        for key, value in data.items():
            if hasattr(instance, key) and getattr(instance, key) != value:
                changes[key] = {'old': getattr(instance, key), 'new': value}
            setattr(instance, key, value)
        
        instance.save()
        
        # Audit logging
        ip, ua = "system", "system"
        if request:
            _, ip, ua = self._get_audit_context(request)
        if changes:
            self._log_update(user, instance, changes, ip, ua)
        
        return instance
    
    def _delete_sync(self, id: int, user=None, request=None):
        """Sync version of delete"""
        instance = self._get_by_id_sync(id, user)
        if not instance:
            return False
        
        self._check_permission(user, instance, 'delete')
        self._soft_delete(instance, user)
        
        # Audit logging
        ip, ua = "system", "system"
        if request:
            _, ip, ua = self._get_audit_context(request)
        self._log_delete(user, instance, ip, ua)
        
        return True
    
    def _list_all_sync(self, user=None, filters: Dict = None, **kwargs):
        """Sync version of list_all"""
        self._check_model_permission(user, 'view')
        queryset = self.model_class.objects.all()
        queryset = self._apply_filters(queryset, filters)
        return list(queryset)
    
    def _save_sync(self, instance, user=None, request=None):
        """Sync version of save"""
        self._check_permission(user, instance, 'update')
        instance.save()
        return instance
    
    def _bulk_create_sync(self, instances: List, user=None, request=None):
        """Sync version of bulk_create"""
        self._check_model_permission(user, 'create')
        return self.model_class.objects.bulk_create(instances)
    
    # ============ ASYNC INTERFACE METHODS ============
    
    async def get_by_id(self, id: int, user=None, **kwargs) -> Optional[E]:
        """Get entity by ID"""
        instance = await sync_to_async(self._get_by_id_sync)(id, user, **kwargs)
        return await self._model_to_entity(instance) if instance else None
    
    async def create(self, data: Dict, user=None, request=None) -> E:
        """Create new entity"""
        instance = await sync_to_async(self._create_sync)(data, user, request)
        return await self._model_to_entity(instance)
    
    async def update(self, id: int, data: Dict, user=None, request=None) -> Optional[E]:
        """Update existing entity"""
        instance = await sync_to_async(self._update_sync)(id, data, user, request)
        return await self._model_to_entity(instance) if instance else None
    
    async def delete(self, id: int, user=None, request=None) -> bool:
        """Delete entity (soft delete)"""
        return await sync_to_async(self._delete_sync)(id, user, request)
    
    async def list_all(self, user=None, filters: Dict = None, **kwargs) -> List[E]:
        """List all entities"""
        instances = await sync_to_async(self._list_all_sync)(user, filters, **kwargs)
        entities = []
        for instance in instances:
            entities.append(await self._model_to_entity(instance))
        return entities
    
    async def save(self, instance, user=None, request=None):
        """Save entity instance"""
        saved_instance = await sync_to_async(self._save_sync)(instance, user, request)
        return await self._model_to_entity(saved_instance)
    
    async def bulk_create(self, instances: List, user=None, request=None):
        """Bulk create entities"""
        created_instances = await sync_to_async(self._bulk_create_sync)(instances, user, request)
        entities = []
        for instance in created_instances:
            entities.append(await self._model_to_entity(instance))
        return entities
    
    # ============ ABSTRACT METHOD FOR ENTITY CONVERSION ============
    
    async def _model_to_entity(self, model_instance) -> E:
        """Convert model instance to entity - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _model_to_entity")