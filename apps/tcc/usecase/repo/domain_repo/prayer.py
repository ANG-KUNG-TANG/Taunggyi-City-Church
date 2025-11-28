# from typing import List, Optional, Dict, Any
# from django.utils import timezone
# from django.db.models import Q
# from asgiref.sync import sync_to_async
# from apps.core.cache.async_cache import AsyncCache
# from apps.tcc.usecase.entities.prayer import PrayerRequestEntity, PrayerResponseEntity 
# from apps.tcc.usecase.repo.base.modelrepo import DomainRepository  
# from apps.tcc.models.prayers.prayer import Prayer, PrayerResponse
# from apps.tcc.models.base.enums import PrayerPrivacy, PrayerCategory, PrayerStatus
# from apps.tcc.utils.audit_logging import AuditLogger  # FIXED IMPORT PATH
# from core.db.decorators import with_db_error_handling, with_retry
# from core.cache.decorator import cached, cache_invalidate
# import logging

# logger = logging.getLogger(__name__)

# class PrayerRequestRepository(DomainRepository):  
#     def __init__(self, cache: AsyncCache = None):
#         super().__init__(Prayer)
#         self.cache = cache
    
#     # ============ CRUD OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "prayer:{prayer_entity.id}",
#             "prayers:public",
#             "prayers:user:{prayer_entity.user_id}",
#             "prayers:category:{prayer_entity.category}",
#             "prayers:list:*"
#         ],
#         namespace="prayers",
#         version="1"
#     )
#     async def create(self, data) -> PrayerRequestEntity:
#         """Create a new prayer request with audit logging"""
#         prayer = await sync_to_async(super().create)(data)
#         prayer_entity = await self._model_to_entity(prayer)
        
#         # FIXED: Use sync_to_async for audit logging
#         await sync_to_async(AuditLogger.log_create)(
#             user=data.get('user'),  # Pass actual user from data
#             model_instance=prayer,
#             ip_address=data.get('ip_address', 'system'),
#             user_agent=data.get('user_agent', 'system')
#         )
        
#         logger.info(f"Prayer request created successfully: {prayer_entity.title}")
#         return prayer_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="prayer:{object_id}",
#         ttl=1800,  # 30 minutes
#         namespace="prayers",
#         version="1"
#     )
#     async def get_by_id(self, object_id, *args, **kwargs) -> Optional[PrayerRequestEntity]:
#         """Get prayer request by ID with caching"""
#         prayer = await sync_to_async(super().get_by_id)(object_id, *args, **kwargs)
#         if not prayer:
#             return None
#         return await self._model_to_entity(prayer)
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "prayer:{object_id}",
#             "prayers:public",
#             "prayers:user:{prayer_entity.user_id}",
#             "prayers:category:{prayer_entity.category}",
#             "prayers:list:*"
#         ],
#         namespace="prayers",
#         version="1"
#     )
#     async def update(self, object_id, data) -> Optional[PrayerRequestEntity]:
#         """Update an existing prayer request with audit logging"""
#         old_prayer = await self._get_by_id_uncached(object_id)
        
#         prayer = await sync_to_async(super().update)(object_id, data)
#         if not prayer:
#             return None
        
#         prayer_entity = await self._model_to_entity(prayer)
        
#         # FIXED: Use sync_to_async for audit logging
#         changes = {
#             'title': {'old': old_prayer.title, 'new': prayer_entity.title},
#             'status': {'old': old_prayer.status, 'new': prayer_entity.status}
#         }
#         await sync_to_async(AuditLogger.log_update)(
#             user=data.get('user'),  # Pass actual user from data
#             model_instance=prayer,
#             changes=changes,
#             ip_address=data.get('ip_address', 'system'),
#             user_agent=data.get('user_agent', 'system')
#         )
        
#         logger.info(f"Prayer request updated successfully: {prayer_entity.title}")
#         return prayer_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "prayer:{object_id}",
#             "prayers:public",
#             "prayers:user:{prayer.user_id}",
#             "prayers:category:{prayer.category}",
#             "prayers:list:*"
#         ],
#         namespace="prayers",
#         version="1"
#     )
#     async def delete(self, object_id) -> bool:
#         """Soft delete a prayer request with audit logging"""
#         prayer = await self._get_by_id_uncached(object_id)
#         if not prayer:
#             return False
        
#         # Store prayer for decorator
#         setattr(self, 'prayer', prayer)
        
#         # FIXED: Use sync_to_async for audit logging
#         await sync_to_async(AuditLogger.log_delete)(
#             user=getattr(prayer, 'user', None),  # Get user from prayer object
#             model_instance=prayer,
#             ip_address="system",
#             user_agent="system"
#         )
        
#         result = await sync_to_async(super().delete)(object_id)
        
#         if result:
#             logger.info(f"Prayer request deleted successfully: {prayer.title}")
        
#         return result
    
#     # ============ QUERY OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="prayers:list:{filters_hash}",
#         ttl=900,  # 15 minutes
#         namespace="prayers",
#         version="1"
#     )
#     async def get_all(self, filters: Dict = None) -> List[PrayerRequestEntity]:
#         """Get all prayer requests with caching"""
#         base_queryset = self.model_class.objects.filter(is_active=True)
        
#         if filters:
#             for key, value in filters.items():
#                 base_queryset = base_queryset.filter(**{key: value})
        
#         # Add filters_hash for decorator
#         filters_hash = hash(str(filters)) if filters else "all"
#         setattr(self, 'filters_hash', filters_hash)
        
#         prayers = []
#         async for prayer in base_queryset.order_by('-created_at'):
#             prayers.append(await self._model_to_entity(prayer))
        
#         return prayers
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="prayers:public:{limit}",
#         ttl=600,  # 10 minutes
#         namespace="prayers",
#         version="1"
#     )
#     async def get_public_prayers(self, limit: int = None) -> List[PrayerRequestEntity]:
#         """Get public prayer requests with caching"""
#         queryset = self.model_class.objects.filter(
#             is_active=True,
#             privacy=PrayerPrivacy.PUBLIC,
#             status=PrayerStatus.ACTIVE
#         ).order_by('-created_at')
        
#         if limit:
#             queryset = queryset[:limit]
        
#         # Add limit for decorator
#         setattr(self, 'limit', limit or 50)
        
#         prayers = []
#         async for prayer in queryset:
#             prayers.append(await self._model_to_entity(prayer))
#         return prayers
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="prayers:user:{user_id}",
#         ttl=1800,  # 30 minutes
#         namespace="prayers",
#         version="1"
#     )
#     async def get_user_prayers(self, user_id: int) -> List[PrayerRequestEntity]:
#         """Get all prayer requests by a user with caching"""
#         # Add user_id for decorator
#         setattr(self, 'user_id', user_id)
        
#         prayers = []
#         async for prayer in self.model_class.objects.filter(
#             user_id=user_id,
#             is_active=True
#         ).order_by('-created_at'):
#             prayers.append(await self._model_to_entity(prayer))
#         return prayers
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="prayers:category:{category}",
#         ttl=1200,  # 20 minutes
#         namespace="prayers",
#         version="1"
#     )
#     async def get_prayers_by_category(self, category: PrayerCategory) -> List[PrayerRequestEntity]:
#         """Get prayers by category with caching"""
#         queryset = self.model_class.objects.filter(
#             is_active=True,
#             category=category,
#             status=PrayerStatus.ACTIVE
#         ).order_by('-created_at')
        
#         prayers = []
#         async for prayer in queryset:
#             prayers.append(await self._model_to_entity(prayer))
#         return prayers
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "prayer:{prayer_id}",
#             "prayers:public",
#             "prayers:user:{user_id}",
#             "prayers:category:{prayer.category}"
#         ],
#         namespace="prayers",
#         version="1"
#     )
#     async def mark_as_answered(self, prayer_id: int, user_id: int, answer_notes: str = "") -> Optional[PrayerRequestEntity]:
#         """Mark prayer request as answered with audit logging"""
#         prayer = await self._get_by_id_uncached(prayer_id)
#         if not prayer:
#             return None
        
#         # Store user_id and prayer for decorator
#         setattr(self, 'user_id', user_id)
#         setattr(self, 'prayer', prayer)
        
#         # Update the prayer
#         update_data = {
#             'is_answered': True,
#             'answer_notes': answer_notes,
#             'status': PrayerStatus.ANSWERED
#         }
        
#         result = await self.update(prayer_id, update_data)
        
#         if result:
#             # FIXED: Use sync_to_async for audit logging
#             await sync_to_async(AuditLogger.log_update)(
#                 user=None,  # You might want to pass the actual user here
#                 model_instance=result,
#                 changes={'status': {'old': PrayerStatus.ACTIVE, 'new': PrayerStatus.ANSWERED}},
#                 ip_address="system",
#                 user_agent="system"
#             )
            
#             logger.info(f"Prayer marked as answered: {result.title}")
        
#         return result
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "prayer:responses:{prayer_id}",
#             "prayer:{prayer_id}"
#         ],
#         namespace="prayers",
#         version="1"
#     )
#     async def add_prayer_response(self, prayer_id: int, user_id: int, content: str, is_private: bool = False) -> Optional[PrayerResponseEntity]:
#         """Add response to prayer request with audit logging"""
#         prayer = await self.get_by_id(prayer_id)
#         if not prayer:
#             return None
        
#         # Create response using PrayerResponseRepository
#         response_repo = PrayerResponseRepository(cache=self.cache)
#         response_data = {
#             'prayer_request_id': prayer_id,
#             'user_id': user_id,
#             'content': content,
#             'is_private': is_private
#         }
        
#         response = await response_repo.create(response_data)
        
#         if response:
#             # FIXED: Use sync_to_async for audit logging
#             await sync_to_async(AuditLogger.log_create)(
#                 user=None,  # You might want to pass the actual user here
#                 model_instance=response,
#                 ip_address="system",
#                 user_agent="system"
#             )
            
#             logger.info(f"Prayer response added to prayer: {prayer.title}")
        
#         return response
    
#     # ============ INTERNAL METHODS ============
    
#     async def _get_by_id_uncached(self, object_id) -> Optional[PrayerRequestEntity]:
#         """Internal method to get prayer by ID without cache"""
#         prayer = await sync_to_async(super().get_by_id)(object_id)
#         if not prayer:
#             return None
#         return await self._model_to_entity(prayer)
    
#     # ============ CONVERSION METHODS ============
    
#     async def _model_to_entity(self, prayer_model) -> PrayerRequestEntity:
#         """Convert Django model to PrayerRequestEntity"""
#         return PrayerRequestEntity(
#             id=prayer_model.id,
#             user_id=prayer_model.user.id if prayer_model.user else None,
#             title=prayer_model.title,
#             content=prayer_model.content,
#             category=prayer_model.category,
#             privacy=prayer_model.privacy,
#             status=prayer_model.status,
#             is_answered=prayer_model.is_answered,
#             answer_notes=prayer_model.answer_notes,
#             is_active=prayer_model.is_active,
#             created_at=prayer_model.created_at,
#             updated_at=prayer_model.updated_at,
#             expires_at=getattr(prayer_model, 'expires_at', None)
#         )


# class PrayerResponseRepository(DomainRepository):
    
#     def __init__(self, cache: AsyncCache = None):
#         super().__init__(PrayerResponse)
#         self.cache = cache
    
#     # ============ CRUD OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "prayer:responses:{data[prayer_request_id]}",
#             "prayer:{data[prayer_request_id]}"
#         ],
#         namespace="prayers",
#         version="1"
#     )
#     async def create(self, data) -> PrayerResponseEntity:
#         """Create a new prayer response with audit logging"""
#         response = await sync_to_async(super().create)(data)
#         response_entity = await self._model_to_entity(response)
        
#         # FIXED: Use sync_to_async for audit logging
#         await sync_to_async(AuditLogger.log_create)(
#             user=data.get('user'),  # Pass actual user from data
#             model_instance=response,
#             ip_address=data.get('ip_address', 'system'),
#             user_agent=data.get('user_agent', 'system')
#         )
        
#         logger.info(f"Prayer response created successfully for request: {response_entity.prayer_request_id}")
#         return response_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="prayer:response:{object_id}",
#         ttl=1800,  # 30 minutes
#         namespace="prayers",
#         version="1"
#     )
#     async def get_by_id(self, object_id, *args, **kwargs) -> Optional[PrayerResponseEntity]:
#         """Get prayer response by ID with caching"""
#         response = await sync_to_async(super().get_by_id)(object_id, *args, **kwargs)
#         if not response:
#             return None
#         return await self._model_to_entity(response)
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "prayer:responses:{response.prayer_request_id}",
#             "prayer:response:{object_id}"
#         ],
#         namespace="prayers",
#         version="1"
#     )
#     async def update(self, object_id, data) -> Optional[PrayerResponseEntity]:
#         """Update an existing prayer response with audit logging"""
#         old_response = await self._get_by_id_uncached(object_id)
        
#         response = await sync_to_async(super().update)(object_id, data)
#         if not response:
#             return None
        
#         response_entity = await self._model_to_entity(response)
        
#         # Store response for decorator
#         setattr(self, 'response', response_entity)
        
#         # FIXED: Use sync_to_async for audit logging
#         changes = {
#             'content': {'old': old_response.content, 'new': response_entity.content}
#         }
#         await sync_to_async(AuditLogger.log_update)(
#             user=data.get('user'),  # Pass actual user from data
#             model_instance=response,
#             changes=changes,
#             ip_address=data.get('ip_address', 'system'),
#             user_agent=data.get('user_agent', 'system')
#         )
        
#         logger.info(f"Prayer response updated successfully: {response_entity.id}")
#         return response_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "prayer:responses:{response.prayer_request_id}",
#             "prayer:response:{object_id}"
#         ],
#         namespace="prayers",
#         version="1"
#     )
#     async def delete(self, object_id) -> bool:
#         """Soft delete a prayer response with audit logging"""
#         response = await self._get_by_id_uncached(object_id)
#         if not response:
#             return False
        
#         # Store response for decorator
#         setattr(self, 'response', response)
        
#         # FIXED: Use sync_to_async for audit logging
#         await sync_to_async(AuditLogger.log_delete)(
#             user=getattr(response, 'user', None),  # Get user from response object
#             model_instance=response,
#             ip_address="system",
#             user_agent="system"
#         )
        
#         result = await sync_to_async(super().delete)(object_id)
        
#         if result:
#             logger.info(f"Prayer response deleted successfully: {response.id}")
        
#         return result
    
#     # ============ QUERY OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="prayer:responses:{prayer_id}",
#         ttl=900,  # 15 minutes
#         namespace="prayers",
#         version="1"
#     )
#     async def get_responses_for_prayer(self, prayer_id: int) -> List[PrayerResponseEntity]:
#         """Get responses for a prayer request with caching"""
#         # Add prayer_id for decorator
#         setattr(self, 'prayer_id', prayer_id)
        
#         responses = []
#         async for response in self.model_class.objects.filter(
#             prayer_request_id=prayer_id,
#             is_active=True
#         ).order_by('created_at'):
#             response_entity = await self._model_to_entity(response)
#             responses.append(response_entity)
        
#         return responses
    
#     # ============ INTERNAL METHODS ============
    
#     async def _get_by_id_uncached(self, object_id) -> Optional[PrayerResponseEntity]:
#         """Internal method to get response by ID without cache"""
#         response = await sync_to_async(super().get_by_id)(object_id)
#         if not response:
#             return None
#         return await self._model_to_entity(response)
    
#     # ============ CONVERSION METHODS ============
    
#     async def _model_to_entity(self, response_model) -> PrayerResponseEntity:
#         """Convert Django model to PrayerResponseEntity"""
#         return PrayerResponseEntity(
#             id=response_model.id,
#             prayer_request_id=response_model.prayer_request.id if response_model.prayer_request else None,
#             user_id=response_model.user.id if response_model.user else None,
#             content=response_model.content,
#             is_private=response_model.is_private,
#             is_active=response_model.is_active,
#             created_at=response_model.created_at,
#             updated_at=response_model.updated_at
#         )