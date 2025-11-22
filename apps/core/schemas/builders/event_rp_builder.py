from typing import Any, Dict, List
from datetime import datetime
from apps.core.schemas.schemas.events import EventResponseSchema, EventListResponseSchema, EventRegistrationResponseSchema, EventRegistrationListResponseSchema
from apps.tcc.usecase.entities.events import EventEntity, EventRegistrationEntity  # Assuming you have these entities

class EventResponseBuilder:
    """
    Centralized builder for creating event response schemas.
    """

    @staticmethod
    def to_response(entity: Any) -> EventResponseSchema:
        """
        Convert an event entity → EventResponseSchema automatically.
        """
        schema_fields = EventResponseSchema.model_fields.keys()
        
        data: Dict[str, Any] = {}
        for field in schema_fields:
            data[field] = getattr(entity, field, None)
        
        # Calculate available spots if max_attendees is set
        if hasattr(entity, 'max_attendees') and entity.max_attendees:
            if hasattr(entity, 'attendee_count'):
                available_spots = max(0, entity.max_attendees - entity.attendee_count)
                data['available_spots'] = available_spots
        
        return EventResponseSchema(**data)

    @staticmethod
    def to_list_response(entities: List[Any], total: int = None, 
                        page: int = 1, per_page: int = 20) -> EventListResponseSchema:
        """
        Convert a list of event entities to a paginated list response.
        """
        event_responses = [EventResponseBuilder.to_response(entity) for entity in entities]
        
        if total is None:
            total = len(entities)
            
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        
        return EventListResponseSchema(
            events=event_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    @staticmethod
    def to_public_response(entity: Any) -> Dict[str, Any]:
        """
        Convert event entity to public response format (for public event listings).
        """
        public_fields = ['id', 'title', 'description', 'location', 'start_date', 'end_date', 
                        'event_type', 'image_url', 'attendee_count', 'available_spots']
        
        data = {}
        for field in public_fields:
            data[field] = getattr(entity, field, None)
        
        return data


class EventRegistrationResponseBuilder:
    """
    Builder for event registration response schemas.
    """

    @staticmethod
    def to_response(entity: Any) -> EventRegistrationResponseSchema:
        """
        Convert an event registration entity → EventRegistrationResponseSchema automatically.
        """
        schema_fields = EventRegistrationResponseSchema.model_fields.keys()
        
        data: Dict[str, Any] = {}
        for field in schema_fields:
            data[field] = getattr(entity, field, None)
        
        return EventRegistrationResponseSchema(**data)

    @staticmethod
    def to_list_response(entities: List[Any], total: int = None, 
                        page: int = 1, per_page: int = 20) -> EventRegistrationListResponseSchema:
        """
        Convert a list of event registration entities to a paginated list response.
        """
        registration_responses = [EventRegistrationResponseBuilder.to_response(entity) for entity in entities]
        
        if total is None:
            total = len(entities)
            
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        
        return EventRegistrationListResponseSchema(
            registrations=registration_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )