# event_update.py
from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.events import EventRepository
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.events import EventEntity
from apps.tcc.models.base.enums import EventStatus, RegistrationStatus
from usecase.domain_exception.e_exceptions import (
    EventException,
    EventNotFoundException
)


class UpdateEventUseCase(BaseUseCase):
    """Use case for updating events"""
    
    def __init__(self):
        super().__init__()
        self.event_repository = EventRepository()  # Instantiate directly
    
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
        
        # Validate date logic if both dates are provided
        start_date = input_data.get('start_date_time')
        end_date = input_data.get('end_date_time')
        
        if start_date and end_date and start_date >= end_date:
            raise EventException(
                message="End date must be after start date",
                error_code="INVALID_DATE_RANGE",
                user_message="Event end date must be after the start date."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        event_id = input_data['event_id']
        
        # Check if event exists
        existing_event = await self.event_repository.get_by_id(event_id)
        if not existing_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found."
            )
        
        # Create updated EventEntity
        update_entity = EventEntity(
            id=event_id,
            title=input_data.get('title', existing_event.title),
            description=input_data.get('description', existing_event.description),
            event_type=input_data.get('event_type', existing_event.event_type),
            status=input_data.get('status', existing_event.status),
            start_date_time=input_data.get('start_date_time', existing_event.start_date_time),
            end_date_time=input_data.get('end_date_time', existing_event.end_date_time),
            location=input_data.get('location', existing_event.location),
            max_attendees=input_data.get('max_attendees', existing_event.max_attendees),
            image_url=input_data.get('image_url', existing_event.image_url),
            is_active=existing_event.is_active,
            created_at=existing_event.created_at,
            updated_at=existing_event.updated_at
        )
        
        # Update event using repository
        updated_event = await self.event_repository.update(event_id, update_entity)
        
        if not updated_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found for update."
            )
        
        return {
            "message": "Event updated successfully",
            "event": self._format_event_response(updated_event)
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


class PublishEventUseCase(BaseUseCase):
    """Use case for publishing events"""
    
    def __init__(self):
        super().__init__()
        self.event_repository = EventRepository()  # Instantiate directly
    
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
        
        # Publish event using repository
        published_event = await self.event_repository.publish(event_id)
        
        if not published_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found for publishing."
            )
        
        return {
            "message": "Event published successfully",
            "event": self._format_event_response(published_event)
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


class CancelEventUseCase(BaseUseCase):
    """Use case for canceling events"""
    
    def __init__(self):
        super().__init__()
        self.event_repository = EventRepository()  # Instantiate directly
    
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
        
        # Cancel event using repository
        cancelled_event = await self.event_repository.cancel(event_id)
        
        if not cancelled_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found for cancellation."
            )
        
        return {
            "message": "Event cancelled successfully",
            "event": self._format_event_response(cancelled_event)
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