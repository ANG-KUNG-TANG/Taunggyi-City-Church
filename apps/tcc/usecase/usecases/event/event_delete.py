from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.events import EventRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.e_exceptions import (
    InvalidEventInputException,
    EventNotFoundException
)
from apps.core.schemas.common.response import APIResponse


class DeleteEventUseCase(BaseUseCase):
    """Use case for soft deleting events"""
    
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
        
        return APIResponse.success_response(
            message="Event deleted successfully",
            data={"event_id": event_id}
        )


class CancelRegistrationUseCase(BaseUseCase):
    """Use case for canceling event registration"""
    
    def __init__(self, event_repository: EventRepository):
        super().__init__()
        self.event_repository = event_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        event_id = input_data.get('event_id')
        if not event_id:
            raise InvalidEventInputException(
                field_errors={"event_id": ["Event ID is required"]},
                user_message="Event ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        event_id = input_data['event_id']
        
        # Cancel registration
        result = await self.event_repository.cancel_registration(
            event_id=event_id,
            user_id=user.id
        )
        
        if not result:
            raise EventNotFoundException(
                event_id=str(event_id),
                user_message="Registration not found or already cancelled."
            )
        
        return APIResponse.success_response(
            message="Event registration cancelled successfully",
            data={"event_id": event_id}
        )