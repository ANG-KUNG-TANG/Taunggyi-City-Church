# prayer_exceptions.py
from typing import Dict, List
from helpers.exceptions.domain.base_exception import BusinessException
from helpers.exceptions.domain.domain_exceptions import ObjectNotFoundException
from .error_codes import ErrorCode, Domain
class PrayerException(BusinessException):
    def __init__(self, message: str, error_code: ErrorCode, details: Dict = None, user_message: str = None):
        super().__init__(
            message=message,
            error_code=error_code,
            domain=Domain.PRAYER,
            status_code=400,
            details=details,
            user_message=user_message
        )

class PrayerRequestNotFoundException(ObjectNotFoundException):
    def __init__(self, prayer_id: str = "", cause: Exception = None):
        super().__init__(
            model="PrayerRequest",
            lookup_params={"id": prayer_id} if prayer_id else {},
            domain=Domain.PRAYER,
            cause=cause
        )

class PrayerRequestNotPublicException(PrayerException):
    def __init__(self, prayer_id: str, privacy_level: str):
        super().__init__(
            message=f"Prayer request {prayer_id} is not publicly accessible",
            error_code=ErrorCode.PRAYER_REQUEST_NOT_PUBLIC,
            details={
                "prayer_id": prayer_id,
                "privacy_level": privacy_level,
                "reason": "Prayer request has restricted visibility"
            },
            user_message="This prayer request is not publicly available."
        )

class PrayerRequestAlreadyAnsweredException(PrayerException):
    def __init__(self, prayer_id: str, answered_at: str):
        super().__init__(
            message=f"Prayer request {prayer_id} is already answered",
            error_code=ErrorCode.PRAYER_REQUEST_ALREADY_ANSWERED,
            details={
                "prayer_id": prayer_id,
                "answered_at": answered_at,
                "reason": "Cannot modify answered prayer request"
            },
            user_message="This prayer request has already been answered."
        )

class PrayerResponseNotAllowedException(PrayerException):
    def __init__(self, prayer_id: str, user_id: str, reason: str):
        super().__init__(
            message=f"User {user_id} cannot respond to prayer {prayer_id}",
            error_code=ErrorCode.PRAYER_RESPONSE_NOT_ALLOWED,
            details={
                "prayer_id": prayer_id,
                "user_id": user_id,
                "reason": reason
            },
            user_message="You are not allowed to respond to this prayer request."
        )

class PrayerCategoryInvalidException(PrayerException):
    def __init__(self, category: str, allowed_categories: List[str]):
        super().__init__(
            message=f"Invalid prayer category: {category}",
            error_code=ErrorCode.PRAYER_CATEGORY_INVALID,
            details={
                "category": category,
                "allowed_categories": allowed_categories,
                "reason": "Category not supported"
            },
            user_message=f"Invalid prayer category. Allowed categories: {', '.join(allowed_categories)}"
        )

class PrayerPrivacyViolationException(PrayerException):
    def __init__(self, prayer_id: str, user_id: str, attempted_action: str):
        super().__init__(
            message=f"Privacy violation for prayer {prayer_id}",
            error_code=ErrorCode.PRAYER_PRIVACY_VIOLATION,
            details={
                "prayer_id": prayer_id,
                "user_id": user_id,
                "attempted_action": attempted_action,
                "reason": "User does not have access due to privacy settings"
            },
            user_message="You do not have permission to access this prayer request."
        )

class PrayerAnswerUpdateException(PrayerException):
    def __init__(self, prayer_id: str, reason: str):
        super().__init__(
            message=f"Cannot update answer for prayer {prayer_id}",
            error_code=ErrorCode.PRAYER_ANSWER_UPDATE_ERROR,
            details={
                "prayer_id": prayer_id,
                "reason": reason
            },
            user_message="Unable to update prayer answer."
        )

class PrayerResponsePrivacyException(PrayerException):
    def __init__(self, response_id: str, user_id: str):
        super().__init__(
            message=f"User {user_id} cannot access private response {response_id}",
            error_code=ErrorCode.PRAYER_RESPONSE_PRIVACY_ERROR,
            details={
                "response_id": response_id,
                "user_id": user_id,
                "reason": "Response is private to prayer request owner"
            },
            user_message="This prayer response is private and cannot be viewed."
        )

class PrayerRequestExpiredException(PrayerException):
    def __init__(self, prayer_id: str, expired_at: str):
        super().__init__(
            message=f"Prayer request {prayer_id} has expired",
            error_code=ErrorCode.PRAYER_REQUEST_EXPIRED,
            details={
                "prayer_id": prayer_id,
                "expired_at": expired_at,
                "reason": "Prayer request is no longer active"
            },
            user_message="This prayer request has expired and is no longer active."
        )