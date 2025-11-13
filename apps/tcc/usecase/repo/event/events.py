from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q
from repo.base.modelrepo import ModelRepository
from apps.tcc.models.events.events import Event, EventRegistration
from apps.tcc.models.base.enums import EventStatus, EventType, RegistrationStatus
from models.base.permission import PermissionDenied
from utils.audit_logging import AuditLogger
from core.db.decorators import with_db_error_handling, with_retry
from entities.events import EventEntity


class EventRepository(ModelRepository[Event]):
    
    def __init__(self):
        super().__init__(Event)
    
    # ============ CRUD OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def create(self, event_entity: EventEntity, user, request=None) -> EventEntity:
        """Create a new event"""
        if not user.can_manage_events:
            raise PermissionDenied("You don't have permission to create events")
        
        # Convert entity to model data
        event_data = self._entity_to_model_data(event_entity)
        event_data['created_by'] = user
        
        # Create event
        event = await self.model_class.objects.acreate(**event_data)
        
        # Get audit context
        context, ip_address, user_agent = await self._get_audit_context(request)
        
        await AuditLogger.log_create(
            user, event, ip_address, user_agent,
            notes=f"Created event: {event.title}"
        )
        
        return await self._model_to_entity(event)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_id(self, id: int, user) -> Optional[EventEntity]:
        """Get event by ID with permission check"""
        try:
            event = await self.model_class.objects.aget(id=id, is_active=True)
            
            # Permission check
            if not await event.can_view(user):
                raise PermissionDenied("You don't have permission to view this event")
            
            return await self._model_to_entity(event)
        except Event.DoesNotExist:
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def update(self, id: int, event_entity: EventEntity, user, request=None) -> Optional[EventEntity]:
        """Update an existing event"""
        existing_event = await self.get_by_id(id, user)
        if not existing_event:
            return None
        
        # Check permission - only event creator or admins can update
        if existing_event.created_by != user and not user.can_manage_events:
            raise PermissionDenied("You can only update events you created")
        
        # Convert entity to update data
        update_data = self._entity_to_model_data(event_entity)
        
        # Update event
        updated_count = await self.model_class.objects.filter(id=id).aupdate(**update_data)
        
        if updated_count:
            # Get audit context
            context, ip_address, user_agent = await self._get_audit_context(request)
            
            updated_event = await self.get_by_id(id, user)
            await AuditLogger.log_update(
                user, updated_event, ip_address, user_agent,
                notes=f"Updated event: {updated_event.title}"
            )
            return updated_event
        
        return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def delete(self, id: int, user, request=None) -> bool:
        """Soft delete an event"""
        event = await self.get_by_id(id, user)
        if not event:
            return False
        
        # Check permission - only event creator or admins can delete
        if event.created_by != user and not user.can_manage_events:
            raise PermissionDenied("You can only delete events you created")
        
        # Get audit context
        context, ip_address, user_agent = await self._get_audit_context(request)
        
        # Soft delete
        deleted_count = await self.model_class.objects.filter(id=id).aupdate(is_active=False)
        
        if deleted_count:
            await AuditLogger.log_delete(
                user, event, ip_address, user_agent,
                notes=f"Deleted event: {event.title}"
            )
            return True
        
        return False
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def publish(self, id: int, user, request=None) -> Optional[EventEntity]:
        """Publish an event"""
        event = await self.get_by_id(id, user)
        if not event:
            return None
        
        # Check permission
        if event.created_by != user and not user.can_manage_events:
            raise PermissionDenied("You can only publish events you created")
        
        # Update status to published
        updated_count = await self.model_class.objects.filter(id=id).aupdate(status=EventStatus.PUBLISHED)
        
        if updated_count:
            # Get audit context
            context, ip_address, user_agent = await self._get_audit_context(request)
            
            published_event = await self.get_by_id(id, user)
            await AuditLogger.log_update(
                user, published_event, 
                {'status': {'old': event.status, 'new': EventStatus.PUBLISHED}},
                ip_address, user_agent,
                notes=f"Published event: {published_event.title}"
            )
            return published_event
        
        return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def cancel(self, id: int, user, request=None) -> Optional[EventEntity]:
        """Cancel an event"""
        event = await self.get_by_id(id, user)
        if not event:
            return None
        
        # Check permission
        if event.created_by != user and not user.can_manage_events:
            raise PermissionDenied("You can only cancel events you created")
        
        # Update status to cancelled
        updated_count = await self.model_class.objects.filter(id=id).aupdate(status=EventStatus.CANCELLED)
        
        if updated_count:
            # Get audit context
            context, ip_address, user_agent = await self._get_audit_context(request)
            
            cancelled_event = await self.get_by_id(id, user)
            await AuditLogger.log_update(
                user, cancelled_event, 
                {'status': {'old': event.status, 'new': EventStatus.CANCELLED}},
                ip_address, user_agent,
                notes=f"Cancelled event: {cancelled_event.title}"
            )
            return cancelled_event
        
        return None
    
    # ============ QUERY OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_all(self, user, filters: Dict = None) -> List[EventEntity]:
        """Get all events with permission filtering"""
        queryset = Event.objects.filter(is_active=True)
        
        if filters:
            for key, value in filters.items():
                queryset = queryset.filter(**{key: value})
        
        # Apply permission filtering
        events = []
        async for event in queryset.order_by('-start_date_time'):
            try:
                if await event.can_view(user):
                    events.append(await self._model_to_entity(event))
            except PermissionDenied:
                continue
        
        return events
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_upcoming_events(self, user, limit: int = None) -> List[EventEntity]:
        """Get upcoming events"""
        now = timezone.now()
        queryset = Event.objects.filter(
            is_active=True,
            status=EventStatus.PUBLISHED,
            start_date_time__gt=now
        ).order_by('start_date_time')
        
        if limit:
            queryset = queryset[:limit]
        
        # Apply permission filtering
        events = []
        async for event in queryset:
            try:
                if await event.can_view(user):
                    events.append(await self._model_to_entity(event))
            except PermissionDenied:
                continue
        
        return events
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_events_by_type(self, event_type: EventType, user) -> List[EventEntity]:
        """Get events by type"""
        queryset = Event.objects.filter(
            is_active=True,
            status=EventStatus.PUBLISHED,
            event_type=event_type
        ).order_by('-start_date_time')
        
        events = []
        async for event in queryset:
            try:
                if await event.can_view(user):
                    events.append(await self._model_to_entity(event))
            except PermissionDenied:
                continue
        
        return events
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_user_events(self, user) -> List[EventEntity]:
        """Get events created by user"""
        if not user.can_manage_events:
            raise PermissionDenied("You don't have permission to view these events")
        
        events = []
        async for event in Event.objects.filter(
            is_active=True,
            created_by=user
        ).order_by('-start_date_time'):
            events.append(await self._model_to_entity(event))
        return events
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def search_events(self, search_term: str, user) -> List[EventEntity]:
        """Search events by title, description, or location"""
        queryset = Event.objects.filter(
            Q(is_active=True) &
            Q(status=EventStatus.PUBLISHED) &
            (Q(title__icontains=search_term) | 
             Q(description__icontains=search_term) |
             Q(location__icontains=search_term))
        ).order_by('-start_date_time')
        
        events = []
        async for event in queryset:
            try:
                if await event.can_view(user):
                    events.append(await self._model_to_entity(event))
            except PermissionDenied:
                continue
        
        return events
    
    # ============ REGISTRATION OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def register_for_event(self, event_id: int, user, request=None) -> Optional[EventRegistration]:
        """Register user for an event"""
        event = await self.get_by_id(event_id, user)
        if not event:
            return None
        
        # Check if user can join events
        if not user.can_join_events:
            raise PermissionDenied("You don't have permission to join events")
        
        # Check if event is full
        if event.max_attendees and event.attendee_count >= event.max_attendees:
            raise ValueError("Event is full")
        
        # Check if already registered
        existing_registration = await EventRegistration.objects.filter(
            event_id=event_id,
            user=user,
            is_active=True
        ).afirst()
        
        if existing_registration:
            raise ValueError("You are already registered for this event")
        
        # Create registration
        registration_data = {
            'event_id': event_id,
            'user': user,
            'status': RegistrationStatus.REGISTERED,
            'registered_at': timezone.now()
        }
        
        registration = EventRegistration(**registration_data)
        
        # Get audit context
        context, ip_address, user_agent = await self._get_audit_context(request)
        
        await registration.asave()
        await AuditLogger.log_create(
            user, registration, ip_address, user_agent,
            notes=f"Registered for event: {event.title}"
        )
        
        return registration
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def cancel_registration(self, event_id: int, user, request=None) -> bool:
        """Cancel event registration"""
        event = await self.get_by_id(event_id, user)
        if not event:
            return False
        
        registration = await EventRegistration.objects.filter(
            event_id=event_id,
            user=user,
            is_active=True
        ).afirst()
        
        if not registration:
            return False
        
        # Get audit context
        context, ip_address, user_agent = await self._get_audit_context(request)
        
        registration.is_active = False
        registration.cancelled_at = timezone.now()
        await registration.asave()
        
        await AuditLogger.log_delete(
            user, registration, ip_address, user_agent,
            notes=f"Cancelled registration for event: {event.title}"
        )
        
        return True
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_event_attendees(self, event_id: int, user) -> List[EventRegistration]:
        """Get event attendees - only event creators and admins can see"""
        event = await self.get_by_id(event_id, user)
        if not event:
            return []
        
        # Check permission
        if event.created_by != user and not user.can_manage_events:
            raise PermissionDenied("You can only view attendees for your own events")
        
        attendees = []
        async for registration in EventRegistration.objects.filter(
            event_id=event_id,
            is_active=True,
            status=RegistrationStatus.REGISTERED
        ).select_related('user'):
            attendees.append(registration)
        return attendees
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_user_registrations(self, user) -> List[EventRegistration]:
        """Get all event registrations for a user"""
        registrations = []
        async for registration in EventRegistration.objects.filter(
            user=user,
            is_active=True
        ).select_related('event').order_by('-registered_at'):
            registrations.append(registration)
        return registrations
    
    # ============ CONVERSION METHODS ============
    
    async def _model_to_entity(self, event_model: Event) -> EventEntity:
        """Convert Django model to EventEntity"""
        return EventEntity(
            id=event_model.id,
            title=event_model.title,
            description=event_model.description,
            event_type=event_model.event_type,
            status=event_model.status,
            start_date_time=event_model.start_date_time,
            end_date_time=event_model.end_date_time,
            location=event_model.location,
            max_attendees=event_model.max_attendees,
            attendee_count=event_model.attendee_count,
            image_url=event_model.image_url,
            is_active=event_model.is_active,
            created_by=event_model.created_by,
            created_at=event_model.created_at,
            updated_at=event_model.updated_at
        )
    
    def _entity_to_model_data(self, event_entity: EventEntity) -> Dict[str, Any]:
        """Convert EventEntity to model data dictionary"""
        return {
            'title': event_entity.title,
            'description': event_entity.description,
            'event_type': event_entity.event_type,
            'status': event_entity.status,
            'start_date_time': event_entity.start_date_time,
            'end_date_time': event_entity.end_date_time,
            'location': event_entity.location,
            'max_attendees': event_entity.max_attendees,
            'image_url': event_entity.image_url,
            'is_active': event_entity.is_active,
        }


class EventRegistrationRepository(ModelRepository[EventRegistration]):
    
    def __init__(self):
        super().__init__(EventRegistration)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_user_registrations(self, user) -> List[EventRegistration]:
        """Get all event registrations for a user"""
        registrations = []
        async for registration in EventRegistration.objects.filter(
            user=user,
            is_active=True
        ).select_related('event').order_by('-registered_at'):
            registrations.append(registration)
        return registrations
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def check_in_attendee(self, registration_id: int, user, request=None) -> Optional[EventRegistration]:
        """Check in attendee - only event creators and admins can do this"""
        registration = await self.get_by_id(registration_id, user)
        if not registration:
            return None
        
        # Check permission
        if registration.event.created_by != user and not user.can_manage_events:
            raise PermissionDenied("You can only check in attendees for your own events")
        
        registration.checked_in = True
        registration.checked_in_at = timezone.now()
        
        context, ip_address, user_agent = await self._get_audit_context(request)
        await registration.asave()
        
        await AuditLogger.log_update(
            user, registration, 
            {'checked_in': {'old': False, 'new': True}},
            ip_address, user_agent,
            notes=f"Checked in attendee: {registration.user.name}"
        )
        
        return registration
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def update_registration_status(self, registration_id: int, status: RegistrationStatus, user, request=None) -> Optional[EventRegistration]:
        """Update registration status"""
        registration = await self.get_by_id(registration_id, user)
        if not registration:
            return None
        
        # Check permission
        if registration.event.created_by != user and not user.can_manage_events:
            raise PermissionDenied("You can only update registrations for your own events")
        
        old_status = registration.status
        registration.status = status
        
        context, ip_address, user_agent = await self._get_audit_context(request)
        await registration.asave()
        
        await AuditLogger.log_update(
            user, registration, 
            {'status': {'old': old_status, 'new': status}},
            ip_address, user_agent,
            notes=f"Updated registration status for: {registration.user.name}"
        )
        
        return registration