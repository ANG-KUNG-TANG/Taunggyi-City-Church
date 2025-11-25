from functools import lru_cache
from apps.tcc.usecase.repo.domain_repo.events import EventRepository

# Import event use cases
from apps.tcc.usecase.usecases.event.event_create import CreateEventUseCase, RegisterForEventUseCase
from apps.tcc.usecase.usecases.event.event_read import (
    GetEventByIdUseCase,
    GetAllEventsUseCase,
    GetUpcomingEventsUseCase,
    GetPublicEventsUseCase,
    GetEventsByTypeUseCase,
    SearchEventsUseCase
)
from apps.tcc.usecase.usecases.event.event_update import UpdateEventUseCase, PublishEventUseCase, CancelEventUseCase
from apps.tcc.usecase.usecases.event.event_delete import DeleteEventUseCase, CancelRegistrationUseCase

# Repository Dependencies
@lru_cache()
def get_event_repository() -> EventRepository:
    """Singleton event repository instance"""
    return EventRepository()

# Create Use Cases
def get_create_event_uc() -> CreateEventUseCase:
    """Create event use case"""
    return CreateEventUseCase(get_event_repository())

def get_register_for_event_uc() -> RegisterForEventUseCase:
    """Register for event use case"""
    return RegisterForEventUseCase(get_event_repository())

# Read Use Cases
def get_event_by_id_uc() -> GetEventByIdUseCase:
    """Get event by ID use case"""
    return GetEventByIdUseCase(get_event_repository())

def get_all_events_uc() -> GetAllEventsUseCase:
    """Get all events use case"""
    return GetAllEventsUseCase(get_event_repository())

def get_upcoming_events_uc() -> GetUpcomingEventsUseCase:
    """Get upcoming events use case"""
    return GetUpcomingEventsUseCase(get_event_repository())

def get_public_events_uc() -> GetPublicEventsUseCase:
    """Get public events use case"""
    return GetPublicEventsUseCase(get_event_repository())

def get_events_by_type_uc() -> GetEventsByTypeUseCase:
    """Get events by type use case"""
    return GetEventsByTypeUseCase(get_event_repository())

def get_search_events_uc() -> SearchEventsUseCase:
    """Search events use case"""
    return SearchEventsUseCase(get_event_repository())

# Update Use Cases
def get_update_event_uc() -> UpdateEventUseCase:
    """Update event use case"""
    return UpdateEventUseCase(get_event_repository())

def get_publish_event_uc() -> PublishEventUseCase:
    """Publish event use case"""
    return PublishEventUseCase(get_event_repository())

def get_cancel_event_uc() -> CancelEventUseCase:
    """Cancel event use case"""
    return CancelEventUseCase(get_event_repository())

# Delete Use Cases
def get_delete_event_uc() -> DeleteEventUseCase:
    """Delete event use case"""
    return DeleteEventUseCase(get_event_repository())

def get_cancel_registration_uc() -> CancelRegistrationUseCase:
    """Cancel registration use case"""
    return CancelRegistrationUseCase(get_event_repository())