from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.events import EventRepository
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.events import EventEntity
from apps.tcc.models.base.enums import EventStatus, EventType
from usecase.domain_exception.e_exceptions import (
    EventException,
    EventScheduleConflictException
)


class CreateEventUseCase(BaseUseCase):
    """Use case for creating new events"""
    
    def __init__(self):
        super().__init__()
        self.event_repository = EventRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_events']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        required_fields = ['title', 'description', 'start_date_time', 'end_date_time', 'location']
        missing_fields = [field for field in required_fields if not input_data.get(field)]
        
        if missing_fields:
            raise EventException(
                message="Missing required fields",
                error_code="MISSING_REQUIRED_FIELDS",
                details={"missing_fields": missing_fields},
                user_message="Please provide all required fields: title, description, start date, end date, and location."
            )
        
        # Validate date logic
        start_date = input_data.get('start_date_time')
        end_date = input_data.get('end_date_time')
        
        if start_date and end_date and start_date >= end_date:
            raise EventException(
                message="End date must be after start date",
                error_code="INVALID_DATE_RANGE",
                user_message="Event end date must be after the start date."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        # Create EventEntity
        event_entity = EventEntity(
            title=input_data['title'],
            description=input_data['description'],
            event_type=input_data.get('event_type', EventType.REGULAR),
            status=input_data.get('status', EventStatus.DRAFT),
            start_date_time=input_data['start_date_time'],
            end_date_time=input_data['end_date_time'],
            location=input_data['location'],
            max_attendees=input_data.get('max_attendees'),
            image_url=input_data.get('image_url')
        )
        
        # Create event using repository
        created_event = await self.event_repository.create(event_entity)
        
        return {
            "message": "Event created successfully",
            "event": self._format_event_response(created_event)
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


class RegisterForEventUseCase(BaseUseCase):
    """Use case for registering for events"""
    
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
                user_message="Event ID is required for registration."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        event_id = input_data['event_id']
        
        # Note: This method would need to be implemented in EventRepository
        # For now, we'll raise an exception indicating it's not implemented
        raise EventException(
            message="Event registration not implemented in repository",
            error_code="NOT_IMPLEMENTED",
            user_message="Event registration is currently not available."
        )