from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q
from repo.base.modelrepo import ModelRepository
from apps.tcc.models.sermons.sermons import Sermon
from apps.tcc.models.base.enums import SermonStatus, MediaType
from utils.audit_logging import AuditLogger
from models.base.permission import PermissionDenied
from core.db.decorators import with_db_error_handling, with_retry


class SermonRepository(ModelRepository[Sermon]):
    
    def __init__(self):
        super().__init__(Sermon)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_recent_sermons(self, user, limit: int = 10) -> List[Sermon]:
        """Get recent published sermons"""
        queryset = Sermon.objects.filter(
            is_active=True,
            status=SermonStatus.PUBLISHED
        ).order_by('-sermon_date')[:limit]
        
        sermons = []
        async for sermon in queryset:
            try:
                if await sermon.can_view(user):
                    sermons.append(sermon)
            except PermissionDenied:
                continue
        
        return sermons
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_sermons_by_preacher(self, preacher: str, user) -> List[Sermon]:
        """Get sermons by preacher"""
        queryset = Sermon.objects.filter(
            is_active=True,
            status=SermonStatus.PUBLISHED,
            preacher__icontains=preacher
        ).order_by('-sermon_date')
        
        sermons = []
        async for sermon in queryset:
            try:
                if await sermon.can_view(user):
                    sermons.append(sermon)
            except PermissionDenied:
                continue
        
        return sermons
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_sermons_by_date_range(self, start_date, end_date, user) -> List[Sermon]:
        """Get sermons by date range"""
        queryset = Sermon.objects.filter(
            is_active=True,
            status=SermonStatus.PUBLISHED,
            sermon_date__range=[start_date, end_date]
        ).order_by('sermon_date')
        
        sermons = []
        async for sermon in queryset:
            try:
                if await sermon.can_view(user):
                    sermons.append(sermon)
            except PermissionDenied:
                continue
        
        return sermons
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def search_sermons(self, search_term: str, user) -> List[Sermon]:
        """Search sermons by title, preacher, or Bible passage"""
        queryset = Sermon.objects.filter(
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
                if await sermon.can_view(user):
                    sermons.append(sermon)
            except PermissionDenied:
                continue
        
        return sermons