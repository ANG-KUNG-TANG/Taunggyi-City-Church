# from typing import List, Optional, Dict, Any
# from django.utils import timezone
# from django.db.models import Q
# from apps.core.cache.async_cache import AsyncCache
# from apps.tcc.usecase.repo.base.modelrepo import DomainRepository  
# from apps.tcc.models.events.events import Event, EventRegistration
# from apps.tcc.models.base.enums import EventStatus, EventType, RegistrationStatus
# from core.db.decorators import with_db_error_handling, with_retry
# from apps.tcc.usecase.entities.events import EventEntity 
# from utils.audit_logging import AuditLogger
# from core.cache.decorator import cached, cache_invalidate
# import logging

# logger = logging.getLogger(__name__)

# class EventRepository(DomainRepository[Event]):
    
#     def __init__(self, cache: AsyncCache = None):
#         super().__init__(Event)
#         self.cache = cache
    
#     # ============ CRUD OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "event:{event_entity.id}",
#             "events:upcoming",
#             "events:published",
#             "events:list:*"
#         ],
#         namespace="events",
#         version="1"
#     )
#     async def create(self, event_entity: EventEntity) -> EventEntity:
#         """Create a new event with audit logging and cache invalidation"""
#         # Convert entity to model data
#         event_data = self._entity_to_model_data(event_entity)
        
#         # Create event
#         event = await self.model_class.objects.acreate(**event_data)
#         event_entity_result = await self._model_to_entity(event)
        
#         # Audit logging
#         await AuditLogger.log_create(
#             user=None,
#             obj=event,
#             notes=f"Created event: {event_entity_result.title}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         logger.info(f"Event created successfully: {event_entity_result.title}")
#         return event_entity_result
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="event:{id}",
#         ttl=3600,  # 1 hour
#         namespace="events",
#         version="1"
#     )
#     async def get_by_id(self, id: int) -> Optional[EventEntity]:
#         """Get event by ID with caching"""
#         try:
#             event = await self.model_class.objects.aget(id=id, is_active=True)
#             return await self._model_to_entity(event)
#         except Event.DoesNotExist:
#             logger.debug(f"Event not found with ID: {id}")
#             return None
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "event:{id}",
#             "events:upcoming",
#             "events:published",
#             "events:list:*"
#         ],
#         namespace="events",
#         version="1"
#     )
#     async def update(self, id: int, event_entity: EventEntity) -> Optional[EventEntity]:
#         """Update an existing event with audit logging"""
#         existing_event = await self._get_by_id_uncached(id)
#         if not existing_event:
#             return None
        
#         # Get old values for audit logging
#         old_title = existing_event.title
#         old_status = existing_event.status
        
#         # Convert entity to update data
#         update_data = self._entity_to_model_data(event_entity)
        
#         # Update event
#         updated_count = await self.model_class.objects.filter(id=id).aupdate(**update_data)
        
#         if updated_count:
#             updated_event = await self._get_by_id_uncached(id)
            
#             # Audit logging
#             changes = {
#                 'title': {'old': old_title, 'new': updated_event.title},
#                 'status': {'old': old_status, 'new': updated_event.status}
#             }
#             await AuditLogger.log_update(
#                 user=None,
#                 obj=updated_event,
#                 changes=changes,
#                 notes=f"Updated event: {updated_event.title}",
#                 ip_address="system",
#                 user_agent="system"
#             )
            
#             logger.info(f"Event updated successfully: {updated_event.title}")
#             return updated_event
        
#         return None
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "event:{id}",
#             "events:upcoming",
#             "events:published",
#             "events:list:*"
#         ],
#         namespace="events",
#         version="1"
#     )
#     async def delete(self, id: int) -> bool:
#         """Soft delete an event with audit logging"""
#         event = await self._get_by_id_uncached(id)
#         if not event:
#             return False
        
#         # Audit logging before deletion
#         await AuditLogger.log_delete(
#             user=None,
#             obj=event,
#             notes=f"Deleted event: {event.title}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         # Soft delete
#         deleted_count = await self.model_class.objects.filter(id=id).aupdate(is_active=False)
        
#         if deleted_count:
#             logger.info(f"Event deleted successfully: {event.title}")
#             return True
        
#         return False
    
#     # ============ EVENT MANAGEMENT OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "event:{id}",
#             "events:upcoming",
#             "events:published"
#         ],
#         namespace="events",
#         version="1"
#     )
#     async def publish(self, id: int) -> Optional[EventEntity]:
#         """Publish an event with audit logging"""
#         event = await self._get_by_id_uncached(id)
#         if not event:
#             return None
        
#         # Update status to published
#         updated_count = await self.model_class.objects.filter(id=id).aupdate(status=EventStatus.PUBLISHED)
        
#         if updated_count:
#             # Audit logging
#             await AuditLogger.log_update(
#                 user=None,
#                 obj=event,
#                 changes={'status': {'old': event.status, 'new': EventStatus.PUBLISHED}},
#                 notes=f"Published event: {event.title}",
#                 ip_address="system",
#                 user_agent="system"
#             )
            
#             logger.info(f"Event published: {event.title}")
#             return await self._get_by_id_uncached(id)
        
#         return None
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "event:{id}",
#             "events:upcoming",
#             "events:published"
#         ],
#         namespace="events",
#         version="1"
#     )
#     async def cancel(self, id: int) -> Optional[EventEntity]:
#         """Cancel an event with audit logging"""
#         event = await self._get_by_id_uncached(id)
#         if not event:
#             return None
        
#         # Update status to cancelled
#         updated_count = await self.model_class.objects.filter(id=id).aupdate(status=EventStatus.CANCELLED)
        
#         if updated_count:
#             # Audit logging
#             await AuditLogger.log_update(
#                 user=None,
#                 obj=event,
#                 changes={'status': {'old': event.status, 'new': EventStatus.CANCELLED}},
#                 notes=f"Cancelled event: {event.title}",
#                 ip_address="system",
#                 user_agent="system"
#             )
            
#             logger.info(f"Event cancelled: {event.title}")
#             return await self._get_by_id_uncached(id)
        
#         return None
    
#     # ============ QUERY OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="events:list:{filters_hash}",
#         ttl=1800,  # 30 minutes
#         namespace="events",
#         version="1"
#     )
#     async def get_all(self, filters: Dict = None) -> List[EventEntity]:
#         """Get all events with caching"""
#         queryset = Event.objects.filter(is_active=True)
        
#         if filters:
#             for key, value in filters.items():
#                 queryset = queryset.filter(**{key: value})
        
#         # Add filters_hash for decorator
#         filters_hash = hash(str(filters)) if filters else "all"
#         setattr(self, 'filters_hash', filters_hash)
        
#         events = []
#         async for event in queryset.order_by('-start_date_time'):
#             events.append(await self._model_to_entity(event))
        
#         return events
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="events:upcoming:{limit}",
#         ttl=900,  # 15 minutes
#         namespace="events",
#         version="1"
#     )
#     async def get_upcoming_events(self, limit: int = None) -> List[EventEntity]:
#         """Get upcoming events with caching"""
#         now = timezone.now()
#         queryset = Event.objects.filter(
#             is_active=True,
#             status=EventStatus.PUBLISHED,
#             start_date_time__gt=now
#         ).order_by('start_date_time')
        
#         if limit:
#             queryset = queryset[:limit]
        
#         # Add limit for decorator
#         setattr(self, 'limit', limit or 10)
        
#         events = []
#         async for event in queryset:
#             events.append(await self._model_to_entity(event))
#         return events
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="events:type:{event_type}",
#         ttl=1800,  # 30 minutes
#         namespace="events",
#         version="1"
#     )
#     async def get_events_by_type(self, event_type: EventType) -> List[EventEntity]:
#         """Get events by type with caching"""
#         queryset = Event.objects.filter(
#             is_active=True,
#             status=EventStatus.PUBLISHED,
#             event_type=event_type
#         ).order_by('-start_date_time')
        
#         events = []
#         async for event in queryset:
#             events.append(await self._model_to_entity(event))
#         return events
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="events:search:{search_term}",
#         ttl=900,  # 15 minutes
#         namespace="events",
#         version="1"
#     )
#     async def search_events(self, search_term: str) -> List[EventEntity]:
#         """Search events by title, description, or location with caching"""
#         queryset = Event.objects.filter(
#             Q(is_active=True) &
#             Q(status=EventStatus.PUBLISHED) &
#             (Q(title__icontains=search_term) | 
#              Q(description__icontains=search_term) |
#              Q(location__icontains=search_term))
#         ).order_by('-start_date_time')
        
#         events = []
#         async for event in queryset:
#             events.append(await self._model_to_entity(event))
#         return events
    
#     # ============ INTERNAL METHODS ============
    
#     async def _get_by_id_uncached(self, id: int) -> Optional[EventEntity]:
#         """Internal method to get event by ID without cache"""
#         try:
#             event = await self.model_class.objects.aget(id=id, is_active=True)
#             return await self._model_to_entity(event)
#         except Event.DoesNotExist:
#             return None
    
#     # ============ CONVERSION METHODS ============
    
#     async def _model_to_entity(self, event_model: Event) -> EventEntity:
#         """Convert Django model to EventEntity"""
#         return EventEntity(
#             id=event_model.id,
#             title=event_model.title,
#             description=event_model.description,
#             event_type=event_model.event_type,
#             status=event_model.status,
#             start_date_time=event_model.start_date_time,
#             end_date_time=event_model.end_date_time,
#             location=event_model.location,
#             max_attendees=event_model.max_attendees,
#             attendee_count=event_model.attendee_count,
#             image_url=event_model.image_url,
#             is_active=event_model.is_active,
#             created_at=event_model.created_at,
#             updated_at=event_model.updated_at
#         )
    
#     def _entity_to_model_data(self, event_entity: EventEntity) -> Dict[str, Any]:
#         """Convert EventEntity to model data dictionary"""
#         return {
#             'title': event_entity.title,
#             'description': event_entity.description,
#             'event_type': event_entity.event_type,
#             'status': event_entity.status,
#             'start_date_time': event_entity.start_date_time,
#             'end_date_time': event_entity.end_date_time,
#             'location': event_entity.location,
#             'max_attendees': event_entity.max_attendees,
#             'image_url': event_entity.image_url,
#             'is_active': event_entity.is_active,
#         }