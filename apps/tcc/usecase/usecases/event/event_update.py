# apps/tcc/usecase/usecases/events/update_event_uc.py
from typing import Dict, Any, List
from apps.core.schemas.builders.event_rp_builder import EventResponseBuilder
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.repo.domain_repo.events import EventRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.e_exceptions import (
    InvalidEventInputException,
    EventNotFoundException,
    EventScheduleConflictException
)
from apps.tcc.usecase.entities.events import EventEntity
from apps.core.schemas.schemas.events import EventUpdateSchema
from apps.tcc.models.base.enums import EventStatus


class UpdateEventUseCase(BaseUseCase):
    """Use case for updating events"""
    
    def __init__(self, event_repository: EventRepository):
        super().__init__()
        self.event_repository = event_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_events']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        event_id = input_data.get('event_id')
        if not event_id:
            raise InvalidEventInputException(
                field_errors={"event_id": ["Event ID is required"]},
                user_message="Event ID is required."
            )
        
        # Validate update data using schema
        update_data = input_data.get('update_data', {})
        try:
            validated_data = EventUpdateSchema(**update_data)
        except Exception as e:
            field_errors = self._extract_pydantic_errors(e)
            raise InvalidEventInputException(
                field_errors=field_errors,
                user_message="Please check your update data and try again."
            )
        
        # Validate date logic if both dates are provided
        start_date = update_data.get('start_date_time')
        end_date = update_data.get('end_date_time')
        
        if start_date and end_date and start_date >= end_date:
            raise InvalidEventInputException(
                field_errors={"end_date_time": ["End date must be after start date"]},
                user_message="Event end date must be after the start date."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        event_id = input_data['event_id']
        update_data = input_data.get('update_data', {})
        
        # Check if event exists
        existing_event = await self.event_repository.get_by_id(event_id)
        if not existing_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found."
            )
        
        # Check for schedule conflicts if dates/location are being updated
        if any(field in update_data for field in ['start_date_time', 'end_date_time', 'location']):
            has_conflict = await self.event_repository.has_schedule_conflict(
                start_date=update_data.get('start_date_time', existing_event.start_date_time),
                end_date=update_data.get('end_date_time', existing_event.end_date_time),
                location=update_data.get('location', existing_event.location),
                exclude_event_id=event_id
            )
            
            if has_conflict:
                raise EventScheduleConflictException(
                    event_id=event_id,
                    conflicting_event_id=None,
                    event_titles=["Conflicting Event"],
                    user_message="There is a scheduling conflict with another event at the same location and time."
                )
        
        # Create updated EventEntity
        updated_event_entity = self._create_updated_entity(existing_event, update_data)
        
        # Update event using repository
        updated_event = await self.event_repository.update(event_id, updated_event_entity)
        
        if not updated_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found for update."
            )
        
        # Use builder for response
        event_response = EventResponseBuilder.to_response(updated_event)
        
        return APIResponse.success_response(
            message="Event updated successfully",
            data=event_response.model_dump()
        )

    def _create_updated_entity(self, existing_event: EventEntity, update_data: Dict[str, Any]) -> EventEntity:
        """Create updated EventEntity from existing event and update data"""
        # Build kwargs for EventEntity constructor
        entity_kwargs = {
            "id": existing_event.id,
            "title": update_data.get('title', existing_event.title),
            "description": update_data.get('description', existing_event.description),
            "event_type": update_data.get('event_type', existing_event.event_type),
            "status": update_data.get('status', existing_event.status),
            "start_date_time": update_data.get('start_date_time', existing_event.start_date_time),
            "end_date_time": update_data.get('end_date_time', existing_event.end_date_time),
            "location": update_data.get('location', existing_event.location),
            "max_attendees": update_data.get('max_attendees', existing_event.max_attendees),
            "image_url": update_data.get('image_url', existing_event.image_url),
            "attendee_count": existing_event.attendee_count,
            "created_by": existing_event.created_by,
            "is_active": existing_event.is_active,
            "created_at": existing_event.created_at,
            "updated_at": existing_event.updated_at
        }
        
        return EventEntity(**entity_kwargs)

    def _extract_pydantic_errors(self, validation_error: Exception) -> Dict[str, List[str]]:
        """Extract field errors from Pydantic validation"""
        field_errors = {}
        if hasattr(validation_error, 'errors'):
            for error in validation_error.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                field_errors.setdefault(field, []).append(error['msg'])
        else:
            field_errors['_form'] = [str(validation_error)]
        return field_errors


class PublishEventUseCase(BaseUseCase):
    """Use case for publishing events"""
    
    def __init__(self, event_repository: EventRepository):
        super().__init__()
        self.event_repository = event_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_events']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        event_id = input_data.get('event_id')
        if not event_id:
            raise InvalidEventInputException(
                field_errors={"event_id": ["Event ID is required"]},
                user_message="Event ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        event_id = input_data['event_id']
        
        # Publish event using repository
        published_event = await self.event_repository.update_status(
            event_id=event_id,
            status=EventStatus.PUBLISHED
        )
        
        if not published_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found for publishing."
            )
        
        event_response = EventResponseBuilder.to_response(published_event)
        
        return APIResponse.success_response(
            message="Event published successfully",
            data=event_response.model_dump()
        )


class CancelEventUseCase(BaseUseCase):
    """Use case for canceling events"""
    
    def __init__(self, event_repository: EventRepository):
        super().__init__()
        self.event_repository = event_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_events']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        event_id = input_data.get('event_id')
        if not event_id:
            raise InvalidEventInputException(
                field_errors={"event_id": ["Event ID is required"]},
                user_message="Event ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        event_id = input_data['event_id']
        
        # Cancel event using repository
        cancelled_event = await self.event_repository.update_status(
            event_id=event_id,
            status=EventStatus.CANCELLED
        )
        
        if not cancelled_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found for cancellation."
            )
        
        event_response = EventResponseBuilder.to_response(cancelled_event)
        
        return APIResponse.success_response(
            message="Event cancelled successfully",
            data=event_response.model_dump()
        )