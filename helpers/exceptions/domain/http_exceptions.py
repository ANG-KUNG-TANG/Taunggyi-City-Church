from http import HTTPStatus
from .base_exception import BusinessException
from .error_codes import ErrorCode
from typing import Dict

class BadRequestException(BusinessException):
    def __init__(self, message: str = "Bad request", details: Dict = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR.value,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details
        )

class UnauthorizedException(BusinessException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_FAILED.value,
            status_code=HTTPStatus.UNAUTHORIZED
        )

class ForbiddenException(BusinessException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            error_code=ErrorCode.PERMISSION_DENIED.value,
            status_code=HTTPStatus.FORBIDDEN
        )

class NotFoundException(BusinessException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND.value,
            status_code=HTTPStatus.NOT_FOUND
        )

class ConflictException(BusinessException):
    def __init__(self, message: str = "Conflict occurred"):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFLICT.value,
            status_code=HTTPStatus.CONFLICT
        )

class UnprocessableEntityException(BusinessException):
    def __init__(self, message: str = "Unprocessable entity", details: Dict = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR.value,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details
        )

class TooManyRequestsException(BusinessException):
    def __init__(self, message: str = "Too many requests", retry_after: int = None):
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED.value,
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            details=details
        )

class PayloadTooLargeException(BusinessException):
    def __init__(self, message: str = "Payload too large"):
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYLOAD_TOO_LARGE.value,
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        )

class ExternalServiceException(BusinessException):
    def __init__(self, message: str = "External service failure", details: Dict = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_FAILURE.value,
            status_code=HTTPStatus.BAD_GATEWAY,
            details=details
        )