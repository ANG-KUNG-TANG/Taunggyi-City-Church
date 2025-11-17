# sermons.py - Fixed Repository Implementation
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q
from asgiref.sync import sync_to_async
from apps.tcc.usecase.entities.sermons import SermonEntity
from repo.base.modelrepo import DomainRepository
from apps.tcc.models.sermons.sermons import Sermon
from apps.tcc.models.base.enums import SermonStatus, MediaType
from utils.audit_logging import AuditLogger
from models.base.permission import PermissionDenied
from core.db.decorators import with_db_error_handling, with_retry


class SermonRepository(DomainRepository):
    
    def __init__(self):
        super().__init__(Sermon)
    
    # ============ CRUD OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def create(self, data, user, request=None) -> SermonEntity:
        """Create a new sermon"""
        sermon = await sync_to_async(super().create)(data, user, request)
        return await self._model_to_entity(sermon)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_id(self, object_id, user, *args, **kwargs) -> Optional[SermonEntity]:
        """Get sermon by ID with permission check"""
        sermon = await sync_to_async(super().get_by_id)(object_id, user, *args, **kwargs)
        if not sermon:
            return None
        return await self._model_to_entity(sermon)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def update(self, object_id, data, user, request=None) -> Optional[SermonEntity]:
        """Update an existing sermon"""
        sermon = await sync_to_async(super().update)(object_id, data, user, request)
        if not sermon:
            return None
        return await self._model_to_entity(sermon)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def delete(self, object_id, user, request=None) -> bool:
        """Soft delete a sermon"""
        return await sync_to_async(super().delete)(object_id, user, request)
    
    # ============ QUERY OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_all(self, user, filters: Dict = None) -> List[SermonEntity]:
        """Get all sermons with permission filtering"""
        if filters:
            queryset = self.model_class.objects.filter(**filters, is_active=True)
        else:
            queryset = self.model_class.objects.filter(is_active=True)
        
        sermons = []
        async for sermon in queryset.order_by('-sermon_date'):
            try:
                # Use the permission check from DomainRepository
                await sync_to_async(self._check_permission)(user, sermon, "view")
                sermons.append(await self._model_to_entity(sermon))
            except PermissionDenied:
                continue
        
        return sermons
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_recent_sermons(self, user, limit: int = 10) -> List[SermonEntity]:
        """Get recent published sermons"""
        queryset = self.model_class.objects.filter(
            is_active=True,
            status=SermonStatus.PUBLISHED
        ).order_by('-sermon_date')[:limit]
        
        sermons = []
        async for sermon in queryset:
            try:
                await sync_to_async(self._check_permission)(user, sermon, "view")
                sermons.append(await self._model_to_entity(sermon))
            except PermissionDenied:
                continue
        
        return sermons
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_sermons_by_preacher(self, preacher: str, user) -> List[SermonEntity]:
        """Get sermons by preacher"""
        queryset = self.model_class.objects.filter(
            is_active=True,
            status=SermonStatus.PUBLISHED,
            preacher__icontains=preacher
        ).order_by('-sermon_date')
        
        sermons = []
        async for sermon in queryset:
            try:
                await sync_to_async(self._check_permission)(user, sermon, "view")
                sermons.append(await self._model_to_entity(sermon))
            except PermissionDenied:
                continue
        
        return sermons
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_sermons_by_date_range(self, start_date, end_date, user) -> List[SermonEntity]:
        """Get sermons by date range"""
        queryset = self.model_class.objects.filter(
            is_active=True,
            status=SermonStatus.PUBLISHED,
            sermon_date__range=[start_date, end_date]
        ).order_by('sermon_date')
        
        sermons = []
        async for sermon in queryset:
            try:
                await sync_to_async(self._check_permission)(user, sermon, "view")
                sermons.append(await self._model_to_entity(sermon))
            except PermissionDenied:
                continue
        
        return sermons
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def search_sermons(self, search_term: str, user) -> List[SermonEntity]:
        """Search sermons by title, preacher, or Bible passage"""
        queryset = self.model_class.objects.filter(
            Q(is_active=True) &
            Q(status=SermonStatus.PUBLISHED) &
            (Q(title__icontains=search_term) | 
             Q(preacher__icontains=search_term) |
             Q(bible_passage__icontains=search_term) |
             Q(description__icontains=search_term))
        ).order_by('-sermon_date')
        
        sermons = []
        async for sermon in queryset:
            try:
                await sync_to_async(self._check_permission)(user, sermon, "view")
                sermons.append(await self._model_to_entity(sermon))
            except PermissionDenied:
                continue
        
        return sermons
    
    # ============ CONVERSION METHODS ============
    
    async def _model_to_entity(self, sermon_model) -> SermonEntity:
        """Convert Django model to SermonEntity"""
        return SermonEntity(
            id=sermon_model.id,
            title=sermon_model.title,
            description=sermon_model.description,
            preacher=sermon_model.preacher,
            bible_passage=sermon_model.bible_passage,
            sermon_date=sermon_model.sermon_date,
            audio_url=sermon_model.audio_url,
            video_url=sermon_model.video_url,
            duration=sermon_model.duration,
            status=sermon_model.status,
            is_active=sermon_model.is_active,
            created_at=sermon_model.created_at,
            updated_at=sermon_model.updated_at
        )