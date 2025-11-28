# from typing import List, Optional, Dict, Any
# from django.utils import timezone
# from django.db.models import Q
# from asgiref.sync import sync_to_async
# from apps.core.cache.async_cache import AsyncCache
# from apps.tcc.usecase.entities.sermons import SermonEntity 
# from apps.tcc.usecase.repo.base.modelrepo import DomainRepository  
# from apps.tcc.models.sermons.sermons import Sermon
# from apps.tcc.models.base.enums import SermonStatus, MediaType
# from utils.audit_logging import AuditLogger
# from core.db.decorators import with_db_error_handling, with_retry
# from core.cache.decorator import cached, cache_invalidate
# import logging

# logger = logging.getLogger(__name__)

# class SermonRepository(DomainRepository):
    
#     def __init__(self, cache: AsyncCache = None):
#         super().__init__(Sermon)
#         self.cache = cache
    
#     # ============ CRUD OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "sermon:{sermon_entity.id}",
#             "sermons:recent",
#             "sermons:preacher:{sermon_entity.preacher}",
#             "sermons:list:*"
#         ],
#         namespace="sermons",
#         version="1"
#     )
#     async def create(self, data) -> SermonEntity:
#         """Create a new sermon with audit logging"""
#         sermon = await sync_to_async(super().create)(data)
#         sermon_entity = await self._model_to_entity(sermon)
        
#         # Audit logging
#         await AuditLogger.log_create(
#             user=None,
#             obj=sermon,
#             notes=f"Created sermon: {sermon_entity.title}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         logger.info(f"Sermon created successfully: {sermon_entity.title}")
#         return sermon_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="sermon:{object_id}",
#         ttl=3600,  # 1 hour
#         namespace="sermons",
#         version="1"
#     )
#     async def get_by_id(self, object_id, *args, **kwargs) -> Optional[SermonEntity]:
#         """Get sermon by ID with caching"""
#         sermon = await sync_to_async(super().get_by_id)(object_id, *args, **kwargs)
#         if not sermon:
#             return None
#         return await self._model_to_entity(sermon)
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "sermon:{object_id}",
#             "sermons:recent",
#             "sermons:preacher:{sermon_entity.preacher}",
#             "sermons:list:*"
#         ],
#         namespace="sermons",
#         version="1"
#     )
#     async def update(self, object_id, data) -> Optional[SermonEntity]:
#         """Update an existing sermon with audit logging"""
#         old_sermon = await self._get_by_id_uncached(object_id)
        
#         sermon = await sync_to_async(super().update)(object_id, data)
#         if not sermon:
#             return None
        
#         sermon_entity = await self._model_to_entity(sermon)
        
#         # Audit logging
#         changes = {
#             'title': {'old': old_sermon.title, 'new': sermon_entity.title},
#             'preacher': {'old': old_sermon.preacher, 'new': sermon_entity.preacher}
#         }
#         await AuditLogger.log_update(
#             user=None,
#             obj=sermon,
#             changes=changes,
#             notes=f"Updated sermon: {sermon_entity.title}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         logger.info(f"Sermon updated successfully: {sermon_entity.title}")
#         return sermon_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "sermon:{object_id}",
#             "sermons:recent",
#             "sermons:preacher:{sermon.preacher}",
#             "sermons:list:*"
#         ],
#         namespace="sermons",
#         version="1"
#     )
#     async def delete(self, object_id) -> bool:
#         """Soft delete a sermon with audit logging"""
#         sermon = await self._get_by_id_uncached(object_id)
#         if not sermon:
#             return False
        
#         # Store sermon for decorator
#         setattr(self, 'sermon', sermon)
        
#         # Audit logging
#         await AuditLogger.log_delete(
#             user=None,
#             obj=sermon,
#             notes=f"Deleted sermon: {sermon.title}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         result = await sync_to_async(super().delete)(object_id)
        
#         if result:
#             logger.info(f"Sermon deleted successfully: {sermon.title}")
        
#         return result
    
#     # ============ QUERY OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="sermons:list:{filters_hash}",
#         ttl=1800,  # 30 minutes
#         namespace="sermons",
#         version="1"
#     )
#     async def get_all(self, filters: Dict = None) -> List[SermonEntity]:
#         """Get all sermons with caching"""
#         if filters:
#             queryset = self.model_class.objects.filter(**filters, is_active=True)
#         else:
#             queryset = self.model_class.objects.filter(is_active=True)
        
#         # Add filters_hash for decorator
#         filters_hash = hash(str(filters)) if filters else "all"
#         setattr(self, 'filters_hash', filters_hash)
        
#         sermons = []
#         async for sermon in queryset.order_by('-sermon_date'):
#             sermons.append(await self._model_to_entity(sermon))
        
#         return sermons
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="sermons:recent:{limit}",
#         ttl=900,  # 15 minutes
#         namespace="sermons",
#         version="1"
#     )
#     async def get_recent_sermons(self, limit: int = 10) -> List[SermonEntity]:
#         """Get recent published sermons with caching"""
#         # Add limit for decorator
#         setattr(self, 'limit', limit)
        
#         queryset = self.model_class.objects.filter(
#             is_active=True,
#             status=SermonStatus.PUBLISHED
#         ).order_by('-sermon_date')[:limit]
        
#         sermons = []
#         async for sermon in queryset:
#             sermons.append(await self._model_to_entity(sermon))
#         return sermons
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="sermons:preacher:{preacher}",
#         ttl=3600,  # 1 hour
#         namespace="sermons",
#         version="1"
#     )
#     async def get_sermons_by_preacher(self, preacher: str) -> List[SermonEntity]:
#         """Get sermons by preacher with caching"""
#         queryset = self.model_class.objects.filter(
#             is_active=True,
#             status=SermonStatus.PUBLISHED,
#             preacher__icontains=preacher
#         ).order_by('-sermon_date')
        
#         sermons = []
#         async for sermon in queryset:
#             sermons.append(await self._model_to_entity(sermon))
#         return sermons
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="sermons:date_range:{start_date}:{end_date}",
#         ttl=1800,  # 30 minutes
#         namespace="sermons",
#         version="1"
#     )
#     async def get_sermons_by_date_range(self, start_date, end_date) -> List[SermonEntity]:
#         """Get sermons by date range with caching"""
#         # Add dates for decorator
#         setattr(self, 'start_date', start_date.isoformat())
#         setattr(self, 'end_date', end_date.isoformat())
        
#         queryset = self.model_class.objects.filter(
#             is_active=True,
#             status=SermonStatus.PUBLISHED,
#             sermon_date__range=[start_date, end_date]
#         ).order_by('sermon_date')
        
#         sermons = []
#         async for sermon in queryset:
#             sermons.append(await self._model_to_entity(sermon))
#         return sermons
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="sermons:search:{search_term}",
#         ttl=600,  # 10 minutes
#         namespace="sermons",
#         version="1"
#     )
#     async def search_sermons(self, search_term: str) -> List[SermonEntity]:
#         """Search sermons by title, preacher, or Bible passage with caching"""
#         queryset = self.model_class.objects.filter(
#             Q(is_active=True) &
#             Q(status=SermonStatus.PUBLISHED) &
#             (Q(title__icontains=search_term) | 
#              Q(preacher__icontains=search_term) |
#              Q(bible_passage__icontains=search_term) |
#              Q(description__icontains=search_term))
#         ).order_by('-sermon_date')
        
#         sermons = []
#         async for sermon in queryset:
#             sermons.append(await self._model_to_entity(sermon))
#         return sermons
    
#     # ============ SERMON MANAGEMENT OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "sermon:{sermon_id}",
#             "sermons:recent",
#             "sermons:list:*"
#         ],
#         namespace="sermons",
#         version="1"
#     )
#     async def publish_sermon(self, sermon_id: int) -> Optional[SermonEntity]:
#         """Publish a sermon with audit logging"""
#         sermon = await self._get_by_id_uncached(sermon_id)
#         if not sermon:
#             return None
        
#         update_data = {
#             'status': SermonStatus.PUBLISHED
#         }
        
#         result = await self.update(sermon_id, update_data)
        
#         if result:
#             # Additional audit logging for publishing
#             await AuditLogger.log_update(
#                 user=None,
#                 obj=result,
#                 changes={'status': {'old': SermonStatus.DRAFT, 'new': SermonStatus.PUBLISHED}},
#                 notes=f"Sermon published: {result.title}",
#                 ip_address="system",
#                 user_agent="system"
#             )
            
#             logger.info(f"Sermon published: {result.title}")
        
#         return result
    
#     # ============ INTERNAL METHODS ============
    
#     async def _get_by_id_uncached(self, object_id) -> Optional[SermonEntity]:
#         """Internal method to get sermon by ID without cache"""
#         sermon = await sync_to_async(super().get_by_id)(object_id)
#         if not sermon:
#             return None
#         return await self._model_to_entity(sermon)
    
#     # ============ CONVERSION METHODS ============
    
#     async def _model_to_entity(self, sermon_model) -> SermonEntity:
#         """Convert Django model to SermonEntity"""
#         return SermonEntity(
#             id=sermon_model.id,
#             title=sermon_model.title,
#             description=sermon_model.description,
#             preacher=sermon_model.preacher,
#             bible_passage=sermon_model.bible_passage,
#             sermon_date=sermon_model.sermon_date,
#             audio_url=sermon_model.audio_url,
#             video_url=sermon_model.video_url,
#             duration=sermon_model.duration,
#             status=sermon_model.status,
#             is_active=sermon_model.is_active,
#             created_at=sermon_model.created_at,
#             updated_at=sermon_model.updated_at
#         )