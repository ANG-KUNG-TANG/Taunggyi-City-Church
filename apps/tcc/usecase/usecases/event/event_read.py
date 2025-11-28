# # apps/tcc/usecase/usecases/events/read_event_uc.py
# from typing import Dict, Any, List
# from apps.core.schemas.builders.event_rp_builder import EventResponseBuilder
# from apps.core.schemas.common.response import APIResponse
# from apps.tcc.usecase.repo.domain_repo.events import EventRepository
# from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.domain_exception.e_exceptions import (
#     InvalidEventInputException,
#     EventNotFoundException
# )
# from apps.tcc.models.base.enums import EventType


# class GetEventByIdUseCase(BaseUseCase):
#     """Use case for getting event by ID"""
    
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
#                 user_message="Event ID is required."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         event_id = input_data['event_id']
#         event_entity = await self.event_repository.get_by_id(event_id)
        
#         if not event_entity:
#             raise EventNotFoundException(
#                 event_id=str(event_id),
#                 user_message="Event not found."
#             )
        
#         # Use builder for response
#         event_response = EventResponseBuilder.to_response(event_entity)
        
#         return APIResponse.success_response(
#             message="Event retrieved successfully",
#             data=event_response.model_dump()
#         )


# class GetAllEventsUseCase(BaseUseCase):
#     """Use case for getting all events with pagination and filtering"""
    
#     def __init__(self, event_repository: EventRepository):
#         super().__init__()
#         self.event_repository = event_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         page = input_data.get('page', 1)
#         per_page = input_data.get('per_page', 20)
#         event_type = input_data.get('event_type')
#         status = input_data.get('status')
        
#         # Get events with pagination
#         events, total_count = await self.event_repository.get_all_paginated(
#             page=page,
#             per_page=per_page,
#             event_type=event_type,
#             status=status
#         )
        
#         # Use builder for list response
#         list_response = EventResponseBuilder.to_list_response(
#             entities=events,
#             total=total_count,
#             page=page,
#             per_page=per_page
#         )
        
#         return APIResponse.success_response(
#             message="Events retrieved successfully",
#             data=list_response.model_dump()
#         )


# class GetUpcomingEventsUseCase(BaseUseCase):
#     """Use case for getting upcoming events"""
    
#     def __init__(self, event_repository: EventRepository):
#         super().__init__()
#         self.event_repository = event_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         limit = input_data.get('limit', 10)
#         page = input_data.get('page', 1)
#         per_page = input_data.get('per_page', 20)
        
#         events, total_count = await self.event_repository.get_upcoming_events_paginated(
#             page=page,
#             per_page=per_page
#         )
        
#         list_response = EventResponseBuilder.to_list_response(
#             entities=events,
#             total=total_count,
#             page=page,
#             per_page=per_page
#         )
        
#         return APIResponse.success_response(
#             message="Upcoming events retrieved successfully",
#             data=list_response.model_dump()
#         )


# class GetPublicEventsUseCase(BaseUseCase):
#     """Use case for getting public events"""
    
#     def __init__(self, event_repository: EventRepository):
#         super().__init__()
#         self.event_repository = event_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = False

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         page = input_data.get('page', 1)
#         per_page = input_data.get('per_page', 20)
        
#         events, total_count = await self.event_repository.get_public_events_paginated(
#             page=page,
#             per_page=per_page
#         )
        
#         # Convert to public responses
#         public_responses = [EventResponseBuilder.to_public_response(event) for event in events]
        
#         return APIResponse.success_response(
#             message="Public events retrieved successfully",
#             data={
#                 "events": public_responses,
#                 "total": total_count,
#                 "page": page,
#                 "per_page": per_page,
#                 "total_pages": (total_count + per_page - 1) // per_page if per_page > 0 else 1
#             }
#         )


# class GetEventsByTypeUseCase(BaseUseCase):
#     """Use case for getting events by type"""
    
#     def __init__(self, event_repository: EventRepository):
#         super().__init__()
#         self.event_repository = event_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         event_type = input_data.get('event_type')
#         if not event_type:
#             raise InvalidEventInputException(
#                 field_errors={"event_type": ["Event type is required"]},
#                 user_message="Event type is required."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         event_type = input_data['event_type']
#         page = input_data.get('page', 1)
#         per_page = input_data.get('per_page', 20)
        
#         events, total_count = await self.event_repository.get_events_by_type_paginated(
#             event_type=event_type,
#             page=page,
#             per_page=per_page
#         )
        
#         list_response = EventResponseBuilder.to_list_response(
#             entities=events,
#             total=total_count,
#             page=page,
#             per_page=per_page
#         )
        
#         return APIResponse.success_response(
#             message=f"Events of type '{event_type}' retrieved successfully",
#             data=list_response.model_dump()
#         )


# class SearchEventsUseCase(BaseUseCase):
#     """Use case for searching events"""
    
#     def __init__(self, event_repository: EventRepository):
#         super().__init__()
#         self.event_repository = event_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         search_term = input_data.get('search_term')
#         if not search_term or len(search_term.strip()) < 2:
#             raise InvalidEventInputException(
#                 field_errors={"search_term": ["Search term must be at least 2 characters long"]},
#                 user_message="Please provide a search term with at least 2 characters."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         search_term = input_data['search_term']
#         page = input_data.get('page', 1)
#         per_page = input_data.get('per_page', 20)
        
#         events, total_count = await self.event_repository.search_events_paginated(
#             search_term=search_term,
#             page=page,
#             per_page=per_page
#         )
        
#         list_response = EventResponseBuilder.to_list_response(
#             entities=events,
#             total=total_count,
#             page=page,
#             per_page=per_page
#         )
        
#         return APIResponse.success_response(
#             message=f"Search results for '{search_term}'",
#             data=list_response.model_dump()
#         )