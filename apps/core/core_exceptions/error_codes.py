from enum import Enum, unique

@unique
class ErrorCode(Enum):
    # Generic Errors
    UNKNOWN = "unknown"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    EXTERNAL_SERVICE_FAILURE = "external_service_failure"
    
    # Authentication & Authorization
    AUTHENTICATION_FAILED = "authentication_failed"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    
    # Database & ORM
    DATABASE_CONNECTION_ERROR = "database_connection_error"
    DATABASE_TIMEOUT = "database_timeout"
    OBJECT_NOT_FOUND = "object_not_found"
    BULK_OPERATION_FAILED = "bulk_operation_failed"
    INTEGRITY_VIOLATION = "integrity_violation"
    DEADLOCK_DETECTED = "deadlock_detected"
    QUERY_EXECUTION_ERROR = "query_execution_error"
    TRANSACTION_ERROR = "transaction_error"
    CONNECTION_POOL_EXHAUSTED = "connection_pool_exhausted"
    DUPLICATE_ENTRY = "duplicate_entry"
    FOREIGN_KEY_VIOLATION = "foreign_key_violation"
    LOCK_WAIT_TIMEOUT = "lock_wait_timeout"
    
    # Church Domain Specific
    USER_ALREADY_EXISTS = "user_already_exists"
    MEMBER_NOT_FOUND = "member_not_found"
    EVENT_FULL = "event_full"
    DONATION_FAILED = "donation_failed"
    INVALID_BAPTISM_DATE = "invalid_baptism_date"
    FAMILY_NOT_FOUND = "family_not_found"
    MINISTRY_NOT_FOUND = "ministry_not_found"
    SACRAMENT_INVALID = "sacrament_invalid"
    
    # External Services
    PAYMENT_SERVICE_UNAVAILABLE = "payment_service_unavailable"
    EMAIL_SERVICE_FAILED = "email_service_failed"
    SMS_SERVICE_FAILED = "sms_service_failed"
    SYSTEM_ERROR = 'system_error'