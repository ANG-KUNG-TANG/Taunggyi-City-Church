from typing import Dict, Any
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.e_exceptions import (
    EventException,
    EventNotFoundException
)


class DeleteEventUseCase(BaseUseCase):
    """Use case for soft deleting events"""
    
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
        existing_event = await self.event_repository.get_by_id(event_id, user)
        if not existing_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found."
            )
        
        # Soft delete event
        result = await self.event_repository.delete(event_id, user)
        
        if not result:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found for deletion."
            )
        
        return {
            "message": "Event deleted successfully",
            "event_id": event_id
        }


class CancelRegistrationUseCase(BaseUseCase):
    """Use case for canceling event registration"""
    
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
        
        result = await self.event_repository.cancel_registration(event_id, user)
        
        if not result:
            raise EventException(
                message=f"Registration for event {event_id} not found",
                error_code="REGISTRATION_NOT_FOUND",
                user_message="Registration not found for cancellation."
            )
        
        return {
            "message": "Event registration cancelled successfully",
            "event_id": event_id
        }