from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.events import EventRepository
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.e_exceptions import (
    EventException,
    EventNotFoundException
)


class DeleteEventUseCase(BaseUseCase):
    """Use case for soft deleting events"""
    
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
        
        # Verify event exists
        existing_event = await self.event_repository.get_by_id(event_id)
        if not existing_event:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Event not found."
            )
        
        # Soft delete event
        result = await self.event_repository.delete(event_id)
        
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
        
        # Note: This method would need to be implemented in EventRepository
        # For now, we'll raise an exception indicating it's not implemented
        raise EventException(
            message="Event registration cancellation not implemented in repository",
            error_code="NOT_IMPLEMENTED",
            user_message="Event registration cancellation is currently not available."
        )