from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q
from asgiref.sync import sync_to_async
from apps.tcc.usecase.entities.prayer import PrayerRequestEntity, PrayerResponseEntity
from repo.base.modelrepo import DomainRepository
from apps.tcc.models.prayers.prayer import PrayerRequest, PrayerResponse
from apps.tcc.models.base.enums import PrayerPrivacy, PrayerCategory, PrayerStatus
from utils.audit_logging import AuditLogger
from models.base.permission import PermissionDenied
from core.db.decorators import with_db_error_handling, with_retry


class PrayerRepository(DomainRepository):
    
    def __init__(self):
        super().__init__(PrayerRequest)
    
    # ============ CRUD OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def create(self, data, user, request=None) -> PrayerRequestEntity:
        """Create a new prayer request"""
        prayer = await sync_to_async(super().create)(data, user, request)
        return await self._model_to_entity(prayer)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_id(self, object_id, user, *args, **kwargs) -> Optional[PrayerRequestEntity]:
        """Get prayer request by ID with permission check"""
        prayer = await sync_to_async(super().get_by_id)(object_id, user, *args, **kwargs)
        if not prayer:
            return None
        return await self._model_to_entity(prayer)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def update(self, object_id, data, user, request=None) -> Optional[PrayerRequestEntity]:
        """Update an existing prayer request"""
        prayer = await sync_to_async(super().update)(object_id, data, user, request)
        if not prayer:
            return None
        return await self._model_to_entity(prayer)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def delete(self, object_id, user, request=None) -> bool:
        """Soft delete a prayer request"""
        return await sync_to_async(super().delete)(object_id, user, request)
    
    # ============ QUERY OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_all(self, user, filters: Dict = None) -> List[PrayerRequestEntity]:
        """Get prayer requests based on user permissions and privacy settings"""
        base_queryset = self.model_class.objects.filter(is_active=True)
        
        if filters:
            for key, value in filters.items():
                base_queryset = base_queryset.filter(**{key: value})
        
        # Apply privacy filtering
        prayers = []
        async for prayer in base_queryset.order_by('-created_at'):
            try:
                prayer_entity = await self._model_to_entity(prayer)
                if prayer_entity.can_view(user):
                    prayers.append(prayer_entity)
            except PermissionDenied:
                continue
        
        return prayers
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_public_prayers(self, user, limit: int = None) -> List[PrayerRequestEntity]:
        """Get public prayer requests"""
        queryset = self.model_class.objects.filter(
            is_active=True,
            privacy=PrayerPrivacy.PUBLIC,
            status=PrayerStatus.ACTIVE
        ).order_by('-created_at')
        
        if limit:
            queryset = queryset[:limit]
        
        prayers = []
        async for prayer in queryset:
            prayers.append(await self._model_to_entity(prayer))
        return prayers
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_user_prayers(self, user) -> List[PrayerRequestEntity]:
        """Get all prayer requests by a user"""
        prayers = []
        async for prayer in self.model_class.objects.filter(
            user=user,
            is_active=True
        ).order_by('-created_at'):
            prayers.append(await self._model_to_entity(prayer))
        return prayers
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_prayers_by_category(self, category: PrayerCategory, user) -> List[PrayerRequestEntity]:
        """Get prayers by category with privacy filtering"""
        queryset = self.model_class.objects.filter(
            is_active=True,
            category=category,
            status=PrayerStatus.ACTIVE
        ).order_by('-created_at')
        
        prayers = []
        async for prayer in queryset:
            try:
                prayer_entity = await self._model_to_entity(prayer)
                if prayer_entity.can_view(user):
                    prayers.append(prayer_entity)
            except PermissionDenied:
                continue
        
        return prayers
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def mark_as_answered(self, prayer_id: int, user, answer_notes: str = "", request=None) -> Optional[PrayerRequestEntity]:
        """Mark prayer request as answered"""
        prayer = await self.get_by_id(prayer_id, user)
        if not prayer:
            return None
        
        # Only the prayer owner or admins can mark as answered
        if prayer.user_id != user.id and not user.can_manage_prayers:
            raise PermissionDenied("You can only mark your own prayers as answered")
        
        # Update the prayer
        update_data = {
            'is_answered': True,
            'answer_notes': answer_notes,
            'status': PrayerStatus.ANSWERED
        }
        
        return await self.update(prayer_id, update_data, user, request)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def add_prayer_response(self, prayer_id: int, user, content: str, is_private: bool = False, request=None) -> Optional[PrayerResponseEntity]:
        """Add response to prayer request"""
        prayer = await self.get_by_id(prayer_id, user)
        if not prayer:
            return None
        
        # Check if user can respond to this prayer
        if not prayer.can_view(user):
            raise PermissionDenied("You cannot respond to this prayer request")
        
        # Create response using PrayerResponseRepository
        response_repo = PrayerResponseRepository()
        response_data = {
            'prayer_request_id': prayer_id,
            'user_id': user.id,
            'content': content,
            'is_private': is_private
        }
        
        return await response_repo.create(response_data, user, request)
    
    # ============ CONVERSION METHODS ============
    
    async def _model_to_entity(self, prayer_model) -> PrayerRequestEntity:
        """Convert Django model to PrayerRequestEntity"""
        return PrayerRequestEntity(
            id=prayer_model.id,
            user_id=prayer_model.user.id if prayer_model.user else None,
            title=prayer_model.title,
            content=prayer_model.content,
            category=prayer_model.category,
            privacy=prayer_model.privacy,
            status=prayer_model.status,
            is_answered=prayer_model.is_answered,
            answer_notes=prayer_model.answer_notes,
            is_active=prayer_model.is_active,
            created_at=prayer_model.created_at,
            updated_at=prayer_model.updated_at,
            expires_at=getattr(prayer_model, 'expires_at', None)
        )


class PrayerResponseRepository(DomainRepository):
    
    def __init__(self):
        super().__init__(PrayerResponse)
    
    # ============ CRUD OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def create(self, data, user, request=None) -> PrayerResponseEntity:
        """Create a new prayer response"""
        response = await sync_to_async(super().create)(data, user, request)
        return await self._model_to_entity(response)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_id(self, object_id, user, *args, **kwargs) -> Optional[PrayerResponseEntity]:
        """Get prayer response by ID with permission check"""
        response = await sync_to_async(super().get_by_id)(object_id, user, *args, **kwargs)
        if not response:
            return None
        return await self._model_to_entity(response)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def update(self, object_id, data, user, request=None) -> Optional[PrayerResponseEntity]:
        """Update an existing prayer response"""
        response = await sync_to_async(super().update)(object_id, data, user, request)
        if not response:
            return None
        return await self._model_to_entity(response)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def delete(self, object_id, user, request=None) -> bool:
        """Soft delete a prayer response"""
        return await sync_to_async(super().delete)(object_id, user, request)
    
    # ============ QUERY OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_responses_for_prayer(self, prayer_id: int, user) -> List[PrayerResponseEntity]:
        """Get responses for a prayer request with privacy filtering"""
        prayer_repo = PrayerRepository()
        prayer = await prayer_repo.get_by_id(prayer_id, user)
        
        if not prayer:
            return []
        
        # Get all responses
        responses = []
        async for response in self.model_class.objects.filter(
            prayer_request_id=prayer_id,
            is_active=True
        ).order_by('created_at'):
            response_entity = await self._model_to_entity(response)
            # Private responses are only visible to the prayer owner
            if response_entity.is_private and prayer.user_id != user.id:
                continue
            responses.append(response_entity)
        
        return responses
    
    # ============ CONVERSION METHODS ============
    
    async def _model_to_entity(self, response_model) -> PrayerResponseEntity:
        """Convert Django model to PrayerResponseEntity"""
        return PrayerResponseEntity(
            id=response_model.id,
            prayer_request_id=response_model.prayer_request.id if response_model.prayer_request else None,
            user_id=response_model.user.id if response_model.user else None,
            content=response_model.content,
            is_private=response_model.is_private,
            is_active=response_model.is_active,
            created_at=response_model.created_at,
            updated_at=response_model.updated_at
        )