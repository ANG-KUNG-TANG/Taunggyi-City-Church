from typing import Dict, Any, List, Optional
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.events import EventEntity
from apps.tcc.models.base.enums import EventType
from usecase.domain_exception.e_exceptions import (
    EventException,
    EventNotFoundException
)


class GetEventByIdUseCase(BaseUseCase):
    """Use case for getting event by ID"""
    
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
        event_entity = await self.event_repository.get_by_id(event_id, user)
        
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
            'created_by': event_entity.created_by.id if event_entity.created_by else None,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class GetAllEventsUseCase(BaseUseCase):
    """Use case for getting all events with optional filtering"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        filters = input_data.get('filters', {})
        events = await self.event_repository.get_all(user, filters)
        
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
            'created_by': event_entity.created_by.id if event_entity.created_by else None,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class GetUpcomingEventsUseCase(BaseUseCase):
    """Use case for getting upcoming events"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        limit = input_data.get('limit')
        events = await self.event_repository.get_upcoming_events(user, limit)
        
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
            'created_by': event_entity.created_by.id if event_entity.created_by else None,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class GetEventsByTypeUseCase(BaseUseCase):
    """Use case for getting events by type"""
    
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
        events = await self.event_repository.get_events_by_type(event_type, user)
        
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
            'created_by': event_entity.created_by.id if event_entity.created_by else None,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class GetUserEventsUseCase(BaseUseCase):
    """Use case for getting events created by user"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_events']

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        events = await self.event_repository.get_user_events(user)
        
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
            'created_by': event_entity.created_by.id if event_entity.created_by else None,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class SearchEventsUseCase(BaseUseCase):
    """Use case for searching events"""
    
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
        events = await self.event_repository.search_events(search_term, user)
        
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
            'created_by': event_entity.created_by.id if event_entity.created_by else None,
            'created_at': event_entity.created_at,
            'updated_at': event_entity.updated_at
        }


class GetEventAttendeesUseCase(BaseUseCase):
    """Use case for getting event attendees"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_events']

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
        
        # Verify event exists
        event_entity = await self.event_repository.get_by_id(event_id, user)
        if not event_entity:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found."
            )
        
        attendees = await self.event_repository.get_event_attendees(event_id, user)
        
        return {
            "event_id": event_id,
            "attendees": [self._format_attendee_response(attendee) for attendee in attendees],
            "total_count": len(attendees)
        }

    @staticmethod
    def _format_attendee_response(registration) -> Dict[str, Any]:
        """Format registration entity for response"""
        return {
            'registration_id': registration.id,
            'user_id': registration.user.id,
            'user_name': registration.user.name,
            'user_email': registration.user.email,
            'status': registration.status.value if hasattr(registration.status, 'value') else registration.status,
            'registered_at': registration.registered_at,
            'checked_in': registration.checked_in,
            'checked_in_at': registration.checked_in_at
        }


class GetUserRegistrationsUseCase(BaseUseCase):
    """Use case for getting user's event registrations"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        registrations = await self.event_repository.get_user_registrations(user)
        
        return {
            "registrations": [self._format_registration_response(registration) for registration in registrations],
            "total_count": len(registrations)
        }

    @staticmethod
    def _format_registration_response(registration) -> Dict[str, Any]:
        """Format registration entity for response"""
        return {
            'registration_id': registration.id,
            'event_id': registration.event.id,
            'event_title': registration.event.title,
            'event_start_date': registration.event.start_date_time,
            'event_location': registration.event.location,
            'status': registration.status.value if hasattr(registration.status, 'value') else registration.status,
            'registered_at': registration.registered_at,
            'checked_in': registration.checked_in,
            'checked_in_at': registration.checked_in_at
        }