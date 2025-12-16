from typing import Dict, List, Optional, Any
from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, EntityNotFoundException, DomainValidationException


class UserException(BaseAppException):
    """Base exception for user-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "USER_ERROR",
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


class InvalidUserInputException(DomainValidationException):
    """Exception for invalid user input validation."""
    
    def __init__(
        self,
        field_errors: Dict[str, List[str]],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message="Invalid user input",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )

class UserAlreadyExistsException(BusinessRuleException):
    """Exception when user with same email/username already exists."""
    
    def __init__(
        self,
        email: Optional[str] = None,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        identifier = email or username
        message = f"User already exists"
        if identifier:
            message = f"User with {'email' if email else 'username'} '{identifier}' already exists"
            
        details = details or {}
        details.update({
            "email": email,
            "username": username,
            "reason": "User with provided credentials already exists"
        })
        
        user_message = "An account with this email already exists. Please use a different email or login."
            
        super().__init__(
            rule_name="UNIQUE_USER_IDENTITY",
            message=message,
            rule_description="User email and username must be unique",
            status_code=409,  
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )

class UserNotFoundException(EntityNotFoundException):
    """Exception when user is not found."""
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict] = None,
        cause: Optional[Exception] = None,
    ):
        lookup_params = {}
        if user_id:
            lookup_params["id"] = user_id
        if email:
            lookup_params["email"] = email
            
        user_message = "User not found."
        if email:
            user_message = f"User with email '{email}' not found."
        elif user_id:
            user_message = f"User with ID '{user_id}' not found."
            
        super().__init__(
            entity_name="User",
            entity_id=user_id,
            lookup_params=lookup_params,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message,
            status_code=404  # HTTP 404 Not Found
        )

class AccountLockedException(BusinessRuleException):
    """Exception when user account is locked."""
    
    def __init__(
        self,
        user_id: str,
        lock_reason: str,
        lock_until: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "lock_reason": lock_reason,
            "lock_until": lock_until,
            "reason": "User account is temporarily locked"
        })
        
        if not user_message:
            user_message = "Your account has been temporarily locked due to multiple failed login attempts."
            if lock_until:
                user_message = f"Your account is locked until {lock_until}. Please try again later."
            else:
                user_message = "Your account has been locked. Please contact support."
                
        super().__init__(
            rule_name="ACCOUNT_SECURITY",
            message=f"User account {user_id} is locked",
            rule_description="Accounts are locked after multiple security violations",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class EmailVerificationException(BusinessRuleException):
    """Exception for email verification issues."""
    
    def __init__(
        self,
        user_id: str,
        email: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "email": email,
            "reason": reason
        })
        
        if not user_message:
            user_message = "Email verification failed."
            if "expired" in reason.lower():
                user_message = "Verification link has expired. Please request a new one."
            elif "invalid" in reason.lower():
                user_message = "Invalid verification link."
                
        super().__init__(
            rule_name="EMAIL_VERIFICATION",
            message=f"Email verification failed for user {user_id}: {reason}",
            rule_description="Users must verify their email address",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class PasswordValidationException(DomainValidationException):
    """Exception for password validation failures."""
    
    def __init__(
        self,
        field_errors: Dict[str, List[str]],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "reason": "Password does not meet security requirements"
        })
        
        if not user_message:
            user_message = "Password does not meet security requirements."
            
        super().__init__(
            message="Password validation failed",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )
        