from typing import Dict
from helpers.exceptions.domain.base_exception import BusinessException
from helpers.exceptions.domain.domain_exceptions import ObjectNotFoundException
from .error_codes import ErrorCode, Domain

class ChatException(BusinessException):
    def __init__(self, message: str, error_code: ErrorCode, details: Dict = None, user_message: str = None):
        super().__init__(
            message=message,
            error_code=error_code,
            domain=Domain.CHAT,
            status_code=400,
            details=details,
            user_message=user_message
        )

class ChatRoomNotFoundException(ObjectNotFoundException):
    def __init__(self, room_id: str = "", cause: Exception = None):
        super().__init__(
            model="ChatRoom",
            lookup_params={"id": room_id} if room_id else {},
            domain=Domain.CHAT,
            cause=cause
        )

class MessageNotFoundException(ObjectNotFoundException):
    def __init__(self, message_id: str = "", cause: Exception = None):
        super().__init__(
            model="ChatMessage",
            lookup_params={"id": message_id} if message_id else {},
            domain=Domain.CHAT,
            cause=cause
        )

class ChatRoomFullException(ChatException):
    def __init__(self, room_id: str, room_name: str, max_participants: int, current_participants: int):
        super().__init__(
            message=f"Chat room {room_name} is full",
            error_code=ErrorCode.CHAT_ROOM_FULL,
            details={
                "room_id": room_id,
                "room_name": room_name,
                "max_participants": max_participants,
                "current_participants": current_participants,
                "reason": "Maximum participant limit reached"
            },
            user_message="This chat room is full. Please try another room."
        )

class MessageSendFailedException(ChatException):
    def __init__(self, room_id: str, user_id: str, reason: str):
        super().__init__(
            message=f"Failed to send message in room {room_id}",
            error_code=ErrorCode.MESSAGE_SEND_FAILED,
            details={
                "room_id": room_id,
                "user_id": user_id,
                "reason": reason
            },
            user_message="Failed to send message. Please try again."
        )

class ChatNotAllowedException(ChatException):
    def __init__(self, user_id: str, room_id: str, reason: str):
        super().__init__(
            message=f"User {user_id} not allowed in chat room {room_id}",
            error_code=ErrorCode.CHAT_NOT_ALLOWED,
            details={
                "user_id": user_id,
                "room_id": room_id,
                "reason": reason
            },
            user_message="You are not allowed to access this chat room."
        )

class MessageEditExpiredException(ChatException):
    def __init__(self, message_id: str, edit_timeout_minutes: int):
        super().__init__(
            message=f"Message {message_id} edit time expired",
            error_code=ErrorCode.MESSAGE_EDIT_EXPIRED,
            details={
                "message_id": message_id,
                "edit_timeout_minutes": edit_timeout_minutes,
                "reason": "Message can only be edited within timeout period"
            },
            user_message=f"Message can only be edited within {edit_timeout_minutes} minutes of sending."
        )

class MessageDeleteExpiredException(ChatException):
    def __init__(self, message_id: str, delete_timeout_minutes: int):
        super().__init__(
            message=f"Message {message_id} delete time expired",
            error_code=ErrorCode.MESSAGE_DELETE_EXPIRED,
            details={
                "message_id": message_id,
                "delete_timeout_minutes": delete_timeout_minutes,
                "reason": "Message can only be deleted within timeout period"
            },
            user_message=f"Message can only be deleted within {delete_timeout_minutes} minutes of sending."
        )

class ChatParticipantLimitException(ChatException):
    def __init__(self, room_id: str, max_participants: int):
        super().__init__(
            message=f"Chat room {room_id} participant limit exceeded",
            error_code=ErrorCode.CHAT_PARTICIPANT_LIMIT,
            details={
                "room_id": room_id,
                "max_participants": max_participants,
                "reason": "Cannot add more participants to chat room"
            },
            user_message="Cannot add more participants to this chat room."
        )

class ChatRoomArchivedException(ChatException):
    def __init__(self, room_id: str, room_name: str):
        super().__init__(
            message=f"Chat room {room_name} is archived",
            error_code=ErrorCode.CHAT_ROOM_ARCHIVED,
            details={
                "room_id": room_id,
                "room_name": room_name,
                "reason": "Chat room is archived and read-only"
            },
            user_message="This chat room is archived and no longer active."
        )