from typing import Dict, List, Optional, Any
from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, EntityNotFoundException


class ChatException(BaseAppException):
    """Base exception for chat-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "CHAT_ERROR",
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


class ChatRoomNotFoundException(EntityNotFoundException):
    """Exception when chat room is not found."""
    
    def __init__(
        self,
        room_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        if not user_message:
            user_message = "Chat room not found."
            
        super().__init__(
            entity_name="ChatRoom",
            entity_id=room_id,
            lookup_params=lookup_params or ({"id": room_id} if room_id else {}),
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class MessageNotFoundException(EntityNotFoundException):
    """Exception when chat message is not found."""
    
    def __init__(
        self,
        message_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        if not user_message:
            user_message = "Message not found."
            
        super().__init__(
            entity_name="ChatMessage",
            entity_id=message_id,
            lookup_params=lookup_params or ({"id": message_id} if message_id else {}),
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class ChatRoomFullException(BusinessRuleException):
    """Exception when chat room is at full capacity."""
    
    def __init__(
        self,
        room_id: str,
        room_name: str,
        max_participants: int,
        current_participants: int,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "room_id": room_id,
            "room_name": room_name,
            "max_participants": max_participants,
            "current_participants": current_participants,
            "reason": "Maximum participant limit reached"
        })
        
        if not user_message:
            user_message = f"Chat room '{room_name}' is full. Maximum capacity is {max_participants} participants."
            
        super().__init__(
            rule_name="CHAT_ROOM_CAPACITY",
            message=f"Chat room {room_name} is full",
            rule_description="Chat room cannot exceed maximum participant limit",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class MessageSendFailedException(ChatException):
    """Exception when message sending fails."""
    
    def __init__(
        self,
        room_id: str,
        user_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "room_id": room_id,
            "user_id": user_id,
            "reason": reason
        })
        
        if not user_message:
            user_message = "Failed to send message. Please try again."
            
        super().__init__(
            message=f"Failed to send message in room {room_id}",
            error_code="MESSAGE_SEND_FAILED",
            status_code=400,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class ChatNotAllowedException(BusinessRuleException):
    """Exception when user is not allowed in chat room."""
    
    def __init__(
        self,
        user_id: str,
        room_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "room_id": room_id,
            "reason": reason
        })
        
        if not user_message:
            user_message = "You are not allowed to access this chat room."
            
        super().__init__(
            rule_name="CHAT_ACCESS_CONTROL",
            message=f"User {user_id} not allowed in chat room {room_id}",
            rule_description="Users must have appropriate permissions to access chat rooms",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )