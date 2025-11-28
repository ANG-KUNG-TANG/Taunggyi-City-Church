# from typing import Dict, Any, List
# from apps.core.schemas.builders.event_rp_builder import EventResponseBuilder
# from apps.core.schemas.common.response import APIResponse
# from apps.tcc.usecase.repo.domain_repo.events import EventRepository
# from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.domain_exception.e_exceptions import (
#     InvalidEventInputException,
#     EventScheduleConflictException
# )
# from apps.tcc.usecase.entities.events import EventEntity
# from apps.core.schemas.schemas.events import EventCreateSchema
# from apps.tcc.models.base.enums import EventStatus, EventType


# class CreateEventUseCase(BaseUseCase):
#     """Use case for creating new events"""
    
#     def __init__(self, event_repository: EventRepository):
#         super().__init__()
#         self.event_repository = event_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_events']

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         # Validate using Pydantic schema
#         try:
#             validated_data = EventCreateSchema(**input_data)
#         except Exception as e:
#             field_errors = self._extract_pydantic_errors(e)
#             raise InvalidEventInputException(
#                 field_errors=field_errors,
#                 user_message="Please check your event data and try again."
#             )

#         # Validate date logic
#         start_date = input_data.get('start_date_time')
#         end_date = input_data.get('end_date_time')
        
#         if start_date and end_date and start_date >= end_date:
#             raise InvalidEventInputException(
#                 field_errors={"end_date_time": ["End date must be after start date"]},
#                 user_message="Event end date must be after the start date."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         # Create EventEntity
#         event_entity = EventEntity(event_data=EventCreateSchema(**input_data))
#         event_entity.prepare_for_persistence()
#         created_event = await self.event_repository.create(event_entity)
                   
#         # Check for schedule conflicts
#         has_conflict = await self.event_repository.has_schedule_conflict(
#             start_date=event_entity.start_date_time,
#             end_date=event_entity.end_date_time,
#             location=event_entity.location
#         )
        
#         if has_conflict:
#             raise EventScheduleConflictException(
#                 event_id=None,
#                 conflicting_event_id=None,
#                 event_titles=["Conflicting Event"],
#                 user_message="There is a scheduling conflict with another event at the same location and time."
#             )
        
#         # Create event using repository
#         created_event = await self.event_repository.create(event_entity)
        
#         # Build response using builder
#         event_response = EventResponseBuilder.to_response(created_event)
        
#         return APIResponse.success_response(
#             message="Event created successfully",
#             data=event_response.model_dump()
#         )

#     def _extract_pydantic_errors(self, validation_error: Exception) -> Dict[str, List[str]]:
#         """Extract field errors from Pydantic validation"""
#         field_errors = {}
#         if hasattr(validation_error, 'errors'):
#             for error in validation_error.errors():
#                 field = ".".join(str(loc) for loc in error['loc'])
#                 field_errors.setdefault(field, []).append(error['msg'])
#         else:
#             field_errors['_form'] = [str(validation_error)]
#         return field_errors


# class RegisterForEventUseCase(BaseUseCase):
#     """Use case for registering for events"""
    
#     def __init__(self, event_repository: EventRepository):
#         super().__init__()
#         self.event_repository = event_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         event_id = input_data.get('event_id')
#         if not event_id:
#             raise InvalidEventInputException(
#                 field_errors={"event_id": ["Event ID is required"]},
#                 user_message="Event ID is required for registration."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         event_id = input_data['event_id']
        
#         # Register user for event
#         registration = await self.event_repository.register_user(
#             event_id=event_id,
#             user_id=user.id
#         )
        
#         if not registration:
#             raise InvalidEventInputException(
#                 field_errors={"event_id": ["Unable to register for event"]},
#                 user_message="Unable to register for this event. It may be full or registration may be closed."
#             )
        
#         return APIResponse.success_response(
#             message="Successfully registered for event",
#             data={
#                 "event_id": event_id,
#                 "user_id": user.id,
#                 "registration_id": registration.id
#             }
#         )