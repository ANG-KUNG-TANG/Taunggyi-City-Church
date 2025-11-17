from typing import Dict, List, Optional, Any
from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, EntityNotFoundException, DomainOperationException


class PrayerException(BaseAppException):
    """Base exception for prayer-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "PRAYER_ERROR",
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


class PrayerRequestNotFoundException(EntityNotFoundException):
    """Exception when prayer request is not found."""
    
    def __init__(
        self,
        prayer_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        if not user_message:
            user_message = "Prayer request not found."
            
        super().__init__(
            entity_name="PrayerRequest",
            entity_id=prayer_id,
            lookup_params=lookup_params or ({"id": prayer_id} if prayer_id else {}),
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class PrayerRequestNotPublicException(BusinessRuleException):
    """Exception when trying to access non-public prayer request."""
    
    def __init__(
        self,
        prayer_id: str,
        privacy_level: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "prayer_id": prayer_id,
            "privacy_level": privacy_level,
            "reason": "Prayer request has restricted visibility"
        })
        
        if not user_message:
            user_message = "This prayer request is private and cannot be accessed."
            
        super().__init__(
            rule_name="PRAYER_REQUEST_PUBLIC_ACCESS",
            message=f"Prayer request {prayer_id} is not publicly accessible",
            rule_description="Only public prayer requests can be accessed without authorization",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class PrayerRequestAlreadyAnsweredException(BusinessRuleException):
    """Exception when trying to modify answered prayer request."""
    
    def __init__(
        self,
        prayer_id: str,
        answered_at: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "prayer_id": prayer_id,
            "answered_at": answered_at,
            "reason": "Cannot modify answered prayer request"
        })
        
        if not user_message:
            user_message = "Answered prayer requests cannot be modified."
            
        super().__init__(
            rule_name="PRAYER_REQUEST_MODIFIABLE",
            message=f"Prayer request {prayer_id} is already answered",
            rule_description="Answered prayer requests cannot be modified",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class PrayerResponseNotAllowedException(BusinessRuleException):
    """Exception when user cannot respond to prayer request."""
    
    def __init__(
        self,
        prayer_id: str,
        user_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "prayer_id": prayer_id,
            "user_id": user_id,
            "reason": reason
        })
        
        if not user_message:
            user_message = "You are not allowed to respond to this prayer request."
            
        super().__init__(
            rule_name="PRAYER_RESPONSE_AUTHORIZATION",
            message=f"User {user_id} cannot respond to prayer {prayer_id}",
            rule_description="Users must have appropriate permissions to respond to prayer requests",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class PrayerCategoryInvalidException(BusinessRuleException):
    """Exception when prayer category is invalid."""
    
    def __init__(
        self,
        category: str,
        allowed_categories: List[str],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "category": category,
            "allowed_categories": allowed_categories,
            "reason": "Category not supported"
        })
        
        if not user_message:
            user_message = f"Category '{category}' is not supported. Allowed categories: {', '.join(allowed_categories)}"
            
        super().__init__(
            rule_name="VALID_PRAYER_CATEGORY",
            message=f"Invalid prayer category: {category}",
            rule_description="Prayer requests must use valid categories",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )