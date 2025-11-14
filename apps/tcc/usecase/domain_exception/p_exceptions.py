from typing import Dict, List, Optional, Any

from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, DomainOperationException, EntityNotFoundException

class PrayerException(BaseAppException):
    """Base exception for prayer-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "PRAYER_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause
        )


class PrayerRequestNotFoundException(EntityNotFoundException):
    def __init__(
        self,
        prayer_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            entity_name="PrayerRequest",
            entity_id=prayer_id,
            lookup_params=lookup_params or ({"id": prayer_id} if prayer_id else {}),
            details=details,
            context=context,
            cause=cause
        )


class PrayerRequestNotPublicException(BusinessRuleException):
    def __init__(
        self,
        prayer_id: str,
        privacy_level: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "prayer_id": prayer_id,
            "privacy_level": privacy_level,
            "reason": "Prayer request has restricted visibility"
        })
            
        super().__init__(
            rule_name="PRAYER_REQUEST_PUBLIC_ACCESS",
            message=f"Prayer request {prayer_id} is not publicly accessible",
            rule_description="Only public prayer requests can be accessed without authorization",
            details=details,
            context=context,
            cause=cause
        )


class PrayerRequestAlreadyAnsweredException(BusinessRuleException):
    def __init__(
        self,
        prayer_id: str,
        answered_at: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "prayer_id": prayer_id,
            "answered_at": answered_at,
            "reason": "Cannot modify answered prayer request"
        })
            
        super().__init__(
            rule_name="PRAYER_REQUEST_MODIFIABLE",
            message=f"Prayer request {prayer_id} is already answered",
            rule_description="Answered prayer requests cannot be modified",
            details=details,
            context=context,
            cause=cause
        )


class PrayerResponseNotAllowedException(BusinessRuleException):
    def __init__(
        self,
        prayer_id: str,
        user_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "prayer_id": prayer_id,
            "user_id": user_id,
            "reason": reason
        })
            
        super().__init__(
            rule_name="PRAYER_RESPONSE_AUTHORIZATION",
            message=f"User {user_id} cannot respond to prayer {prayer_id}",
            rule_description="Users must have appropriate permissions to respond to prayer requests",
            details=details,
            context=context,
            cause=cause
        )


class PrayerCategoryInvalidException(BusinessRuleException):
    def __init__(
        self,
        category: str,
        allowed_categories: List[str],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "category": category,
            "allowed_categories": allowed_categories,
            "reason": "Category not supported"
        })
            
        super().__init__(
            rule_name="VALID_PRAYER_CATEGORY",
            message=f"Invalid prayer category: {category}",
            rule_description="Prayer requests must use valid categories",
            details=details,
            context=context,
            cause=cause
        )


class PrayerPrivacyViolationException(BusinessRuleException):
    def __init__(
        self,
        prayer_id: str,
        user_id: str,
        attempted_action: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "prayer_id": prayer_id,
            "user_id": user_id,
            "attempted_action": attempted_action,
            "reason": "User does not have access due to privacy settings"
        })
            
        super().__init__(
            rule_name="PRAYER_PRIVACY_COMPLIANCE",
            message=f"Privacy violation for prayer {prayer_id}",
            rule_description="Users can only access prayer requests according to privacy settings",
            details=details,
            context=context,
            cause=cause
        )


class PrayerAnswerUpdateException(DomainOperationException):
    def __init__(
        self,
        prayer_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "prayer_id": prayer_id,
            "reason": reason
        })
            
        super().__init__(
            operation="update_answer",
            entity_name="PrayerRequest",
            reason=reason,
            details=details,
            context=context,
            cause=cause
        )


class PrayerResponsePrivacyException(BusinessRuleException):
    def __init__(
        self,
        response_id: str,
        user_id: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "response_id": response_id,
            "user_id": user_id,
            "reason": "Response is private to prayer request owner"
        })
            
        super().__init__(
            rule_name="PRAYER_RESPONSE_PRIVACY",
            message=f"User {user_id} cannot access private response {response_id}",
            rule_description="Prayer responses follow the privacy settings of the original request",
            details=details,
            context=context,
            cause=cause
        )


class PrayerRequestExpiredException(BusinessRuleException):
    def __init__(
        self,
        prayer_id: str,
        expired_at: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "prayer_id": prayer_id,
            "expired_at": expired_at,
            "reason": "Prayer request is no longer active"
        })
            
        super().__init__(
            rule_name="PRAYER_REQUEST_ACTIVE",
            message=f"Prayer request {prayer_id} has expired",
            rule_description="Expired prayer requests cannot be modified or responded to",
            details=details,
            context=context,
            cause=cause
        )