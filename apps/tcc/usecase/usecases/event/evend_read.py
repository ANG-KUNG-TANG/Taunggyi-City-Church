# evend_read.py (corrected to event_read.py)
from typing import Dict, Any, List, Optional
from apps.tcc.usecase.repo.domain_repo.events import EventRepository
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.events import EventEntity
from apps.tcc.models.base.enums import EventType
from usecase.domain_exception.e_exceptions import (
    EventException,
    EventNotFoundException
)


class GetEventByIdUseCase(BaseUseCase):
    """Use case for getting event by ID"""
    
    def __init__(self):
        super().__init__()
        self.event_repository = EventRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        event_id = input_data.get('event_id')
        if not event_id:
            raise EventException(
                message="Event ID is required",
                error_code="MISSING_EVENT_ID",
                user_message="Event ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        event_id = input_data['event_id']
        event_entity = await self.event_repository.get_by_id(event_id)
        
        if not event_entity:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found."
            )
        
        return {
            "event": self._format_event_response(event_entity)
        }

    @staticmethod
    def _format_event_response(event_entity: EventEntity) -> Dict[str, Any]:
        """Format event entity for response"""
        return {
            'id': event_entity.id,
            'title': event_entity.title,
            'description': event_entity.description,
            'event_type': event_entity.event_type.value if hasattr(event_entity.event_type, 'value') else event_entity.event_type,
            'status': event_entity.status.value if hasattr(event_entity.status, 'value') else event_entity.status,
            'start_date_time': event_entity.start_date_time,
            'end_date_time': event_entity.end_date_time,
            'location': event_entity.location,
            'max_attendees': event_entity.max_attendees,
            'attendee_count': event_entity.attendee_count,
            'image_url': event_entity.image_url,
            'is_active': event_entity.is_active,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class GetAllEventsUseCase(BaseUseCase):
    """Use case for getting all events with optional filtering"""
    
    def __init__(self):
        super().__init__()
        self.event_repository = EventRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        filters = input_data.get('filters', {})
        events = await self.event_repository.get_all(filters)
        
        return {
            "events": [self._format_event_response(event) for event in events],
            "total_count": len(events)
        }

    @staticmethod
    def _format_event_response(event_entity: EventEntity) -> Dict[str, Any]:
        """Format event entity for response"""
        return {
            'id': event_entity.id,
            'title': event_entity.title,
            'description': event_entity.description,
            'event_type': event_entity.event_type.value if hasattr(event_entity.event_type, 'value') else event_entity.event_type,
            'status': event_entity.status.value if hasattr(event_entity.status, 'value') else event_entity.status,
            'start_date_time': event_entity.start_date_time,
            'end_date_time': event_entity.end_date_time,
            'location': event_entity.location,
            'max_attendees': event_entity.max_attendees,
            'attendee_count': event_entity.attendee_count,
            'image_url': event_entity.image_url,
            'is_active': event_entity.is_active,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class GetUpcomingEventsUseCase(BaseUseCase):
    """Use case for getting upcoming events"""
    
    def __init__(self):
        super().__init__()
        self.event_repository = EventRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        limit = input_data.get('limit')
        events = await self.event_repository.get_upcoming_events(limit)
        
        return {
            "events": [self._format_event_response(event) for event in events],
            "total_count": len(events)
        }

    @staticmethod
    def _format_event_response(event_entity: EventEntity) -> Dict[str, Any]:
        """Format event entity for response"""
        return {
            'id': event_entity.id,
            'title': event_entity.title,
            'description': event_entity.description,
            'event_type': event_entity.event_type.value if hasattr(event_entity.event_type, 'value') else event_entity.event_type,
            'status': event_entity.status.value if hasattr(event_entity.status, 'value') else event_entity.status,
            'start_date_time': event_entity.start_date_time,
            'end_date_time': event_entity.end_date_time,
            'location': event_entity.location,
            'max_attendees': event_entity.max_attendees,
            'attendee_count': event_entity.attendee_count,
            'image_url': event_entity.image_url,
            'is_active': event_entity.is_active,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class GetEventsByTypeUseCase(BaseUseCase):
    """Use case for getting events by type"""
    
    def __init__(self):
        super().__init__()
        self.event_repository = EventRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        event_type = input_data.get('event_type')
        if not event_type:
            raise EventException(
                message="Event type is required",
                error_code="MISSING_EVENT_TYPE",
                user_message="Event type is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        event_type = input_data['event_type']
        events = await self.event_repository.get_events_by_type(event_type)
        
        return {
            "events": [self._format_event_response(event) for event in events],
            "event_type": event_type.value if hasattr(event_type, 'value') else event_type,
            "total_count": len(events)
        }

    @staticmethod
    def _format_event_response(event_entity: EventEntity) -> Dict[str, Any]:
        """Format event entity for response"""
        return {
            'id': event_entity.id,
            'title': event_entity.title,
            'description': event_entity.description,
            'event_type': event_entity.event_type.value if hasattr(event_entity.event_type, 'value') else event_entity.event_type,
            'status': event_entity.status.value if hasattr(event_entity.status, 'value') else event_entity.status,
            'start_date_time': event_entity.start_date_time,
            'end_date_time': event_entity.end_date_time,
            'location': event_entity.location,
            'max_attendees': event_entity.max_attendees,
            'attendee_count': event_entity.attendee_count,
            'image_url': event_entity.image_url,
            'is_active': event_entity.is_active,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class SearchEventsUseCase(BaseUseCase):
    """Use case for searching events"""
    
    def __init__(self):
        super().__init__()
        self.event_repository = EventRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        search_term = input_data.get('search_term')
        if not search_term:
            raise EventException(
                message="Search term is required",
                error_code="MISSING_SEARCH_TERM",
                user_message="Please provide a search term."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        search_term = input_data['search_term']
        events = await self.event_repository.search_events(search_term)
        
        return {
            "events": [self._format_event_response(event) for event in events],
            "search_term": search_term,
            "total_count": len(events)
        }

    @staticmethod
    def _format_event_response(event_entity: EventEntity) -> Dict[str, Any]:
        """Format event entity for response"""
        return {
            'id': event_entity.id,
            'title': event_entity.title,
            'description': event_entity.description,
            'event_type': event_entity.event_type.value if hasattr(event_entity.event_type, 'value') else event_entity.event_type,
            'status': event_entity.status.value if hasattr(event_entity.status, 'value') else event_entity.status,
            'start_date_time': event_entity.start_date_time,
            'end_date_time': event_entity.end_date_time,
            'location': event_entity.location,
            'max_attendees': event_entity.max_attendees,
            'attendee_count': event_entity.attendee_count,
            'image_url': event_entity.image_url,
            'is_active': event_entity.is_active,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }