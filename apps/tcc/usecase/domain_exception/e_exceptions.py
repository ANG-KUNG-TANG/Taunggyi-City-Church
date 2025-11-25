from typing import Dict, List, Optional, Any
from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, EntityNotFoundException


class EventException(BaseAppException):
    """Base exception for event-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "EVENT_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class InvalidEventInputException(EventException):
    def __init__(
        self,
        field_errors: Dict[str, List[str]],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        # Call parent constructor correctly
        super().__init__(
            message="Invalid Event input",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )
        
class EventNotFoundException(EntityNotFoundException):
    """Exception when event is not found."""
    
    def __init__(
        self,
        event_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        if not user_message:
            user_message = "Event not found."
            
        super().__init__(
            entity_name="Event",
            entity_id=event_id,
            lookup_params=lookup_params or ({"id": event_id} if event_id else {}),
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class EventRegistrationException(EventException):
    """Base exception for event registration errors."""
    
    def __init__(
        self,
        message: str,
        event_id: str,
        user_id: str,
        error_code: str = "EVENT_REGISTRATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "event_id": event_id,
            "user_id": user_id
        })
            
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class EventFullException(EventRegistrationException):
    """Exception when event is at full capacity."""
    
    def __init__(
        self,
        event_id: str,
        user_id: str,
        event_title: str,
        max_attendees: int,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "event_title": event_title,
            "max_attendees": max_attendees,
            "reason": "Maximum attendee limit reached"
        })
        
        if not user_message:
            user_message = f"Event '{event_title}' is full. Maximum capacity is {max_attendees} attendees."
            
        super().__init__(
            message=f"Event {event_title} is full",
            error_code="EVENT_FULL",
            event_id=event_id,
            user_id=user_id,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class AlreadyRegisteredException(EventRegistrationException):
    """Exception when user is already registered for event."""
    
    def __init__(
        self,
        event_id: str,
        user_id: str,
        event_title: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "event_title": event_title,
            "reason": "User already registered for this event"
        })
        
        if not user_message:
            user_message = f"You are already registered for '{event_title}'."
            
        super().__init__(
            message=f"User {user_id} already registered for event {event_title}",
            error_code="ALREADY_REGISTERED",
            event_id=event_id,
            user_id=user_id,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class EventRegistrationClosedException(EventRegistrationException):
    """Exception when event registration is closed."""
    
    def __init__(
        self,
        event_id: str,
        user_id: str,
        event_title: str,
        registration_deadline: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "event_title": event_title,
            "registration_deadline": registration_deadline,
            "reason": "Registration period has ended"
        })
        
        if not user_message:
            user_message = f"Registration for '{event_title}' has closed."
            
        super().__init__(
            message=f"Registration closed for event {event_title}",
            error_code="EVENT_REGISTRATION_CLOSED",
            event_id=event_id,
            user_id=user_id,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class EventScheduleConflictException(BusinessRuleException):
    """Exception when events have scheduling conflicts."""
    
    def __init__(
        self,
        event_id: str,
        conflicting_event_id: str,
        event_titles: List[str],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "event_id": event_id,
            "conflicting_event_id": conflicting_event_id,
            "event_titles": event_titles,
            "reason": "Events have overlapping schedules"
        })
        
        if not user_message:
            user_message = "This event conflicts with another event in your schedule."
            
        super().__init__(
            rule_name="EVENT_SCHEDULING",
            message=f"Schedule conflict between events",
            rule_description="Events cannot have overlapping schedules for the same venue/resources",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )