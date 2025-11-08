# event_exceptions.py
from typing import Dict, List
from helpers.exceptions.domain.base_exception import BusinessException
from helpers.exceptions.domain.domain_exceptions import ObjectNotFoundException
from .error_codes import ErrorCode, Domain

class EventException(BusinessException):
    def __init__(self, message: str, error_code: ErrorCode, details: Dict = None, user_message: str = None):
        super().__init__(
            message=message,
            error_code=error_code,
            domain=Domain.EVENT,
            status_code=400,
            details=details,
            user_message=user_message
        )

class EventNotFoundException(ObjectNotFoundException):
    def __init__(self, event_id: str = "", cause: Exception = None):
        super().__init__(
            model="Event",
            lookup_params={"id": event_id} if event_id else {},
            domain=Domain.EVENT,
            cause=cause
        )

class EventRegistrationException(EventException):
    def __init__(self, message: str, error_code: ErrorCode, event_id: str, user_id: str, details: Dict = None):
        base_details = {"event_id": event_id, "user_id": user_id}
        if details: base_details.update(details)
        
        super().__init__(
            message=message,
            error_code=error_code,
            details=base_details
        )

class EventFullException(EventRegistrationException):
    def __init__(self, event_id: str, user_id: str, event_title: str, max_attendees: int):
        super().__init__(
            message=f"Event {event_title} is full",
            error_code=ErrorCode.EVENT_FULL,
            event_id=event_id,
            user_id=user_id,
            details={
                "event_title": event_title,
                "max_attendees": max_attendees,
                "reason": "Maximum attendee limit reached"
            },
            user_message="This event is currently full. Please try another event."
        )

class AlreadyRegisteredException(EventRegistrationException):
    def __init__(self, event_id: str, user_id: str, event_title: str):
        super().__init__(
            message=f"User {user_id} already registered for event {event_title}",
            error_code=ErrorCode.ALREADY_REGISTERED,
            event_id=event_id,
            user_id=user_id,
            details={
                "event_title": event_title,
                "reason": "User already registered for this event"
            },
            user_message="You are already registered for this event."
        )

class NotRegisteredException(EventRegistrationException):
    def __init__(self, event_id: str, user_id: str, event_title: str):
        super().__init__(
            message=f"User {user_id} not registered for event {event_title}",
            error_code=ErrorCode.NOT_REGISTERED,
            event_id=event_id,
            user_id=user_id,
            details={
                "event_title": event_title,
                "reason": "User not registered for this event"
            },
            user_message="You are not registered for this event."
        )

class EventRegistrationClosedException(EventRegistrationException):
    def __init__(self, event_id: str, user_id: str, event_title: str, registration_deadline: str):
        super().__init__(
            message=f"Registration closed for event {event_title}",
            error_code=ErrorCode.EVENT_REGISTRATION_CLOSED,
            event_id=event_id,
            user_id=user_id,
            details={
                "event_title": event_title,
                "registration_deadline": registration_deadline,
                "reason": "Registration period has ended"
            },
            user_message="Registration for this event has closed."
        )

class EventScheduleConflictException(EventException):
    def __init__(self, event_id: str, conflicting_event_id: str, event_titles: List[str]):
        super().__init__(
            message=f"Schedule conflict between events",
            error_code=ErrorCode.EVENT_SCHEDULE_CONFLICT,
            details={
                "event_id": event_id,
                "conflicting_event_id": conflicting_event_id,
                "event_titles": event_titles,
                "reason": "Events have overlapping schedules"
            },
            user_message="This event conflicts with another event in your schedule."
        )

class EventPublishException(EventException):
    def __init__(self, event_id: str, event_title: str, reason: str):
        super().__init__(
            message=f"Cannot publish event {event_title}",
            error_code=ErrorCode.EVENT_PUBLISH_ERROR,
            details={
                "event_id": event_id,
                "event_title": event_title,
                "reason": reason
            },
            user_message="Unable to publish event. Please check event details."
        )

class EventCancelException(EventException):
    def __init__(self, event_id: str, event_title: str, reason: str):
        super().__init__(
            message=f"Cannot cancel event {event_title}",
            error_code=ErrorCode.EVENT_CANCEL_ERROR,
            details={
                "event_id": event_id,
                "event_title": event_title,
                "reason": reason
            },
            user_message="Unable to cancel event. Event may have already started or been completed."
        )

class CheckinExpiredException(EventRegistrationException):
    def __init__(self, event_id: str, user_id: str, event_title: str, checkin_deadline: str):
        super().__init__(
            message=f"Check-in expired for event {event_title}",
            error_code=ErrorCode.CHECKIN_EXPIRED,
            event_id=event_id,
            user_id=user_id,
            details={
                "event_title": event_title,
                "checkin_deadline": checkin_deadline,
                "reason": "Check-in period has ended"
            },
            user_message="Check-in for this event has expired."
        )

class EventCancelledException(EventException):
    def __init__(self, event_id: str, event_title: str):
        super().__init__(
            message=f"Event {event_title} is cancelled",
            error_code=ErrorCode.EVENT_CANCELLED,
            details={
                "event_id": event_id,
                "event_title": event_title,
                "reason": "Event has been cancelled"
            },
            user_message="This event has been cancelled."
        )

class EventNotStartedException(EventException):
    def __init__(self, event_id: str, event_title: str, start_time: str):
        super().__init__(
            message=f"Event {event_title} has not started",
            error_code=ErrorCode.EVENT_NOT_STARTED,
            details={
                "event_id": event_id,
                "event_title": event_title,
                "start_time": start_time,
                "reason": "Event has not started yet"
            },
            user_message="This event has not started yet."
        )

class EventEndedException(EventException):
    def __init__(self, event_id: str, event_title: str, end_time: str):
        super().__init__(
            message=f"Event {event_title} has ended",
            error_code=ErrorCode.EVENT_ENDED,
            details={
                "event_id": event_id,
                "event_title": event_title,
                "end_time": end_time,
                "reason": "Event has already ended"
            },
            user_message="This event has already ended."
        )