from typing import Dict, List, Optional, Any
from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, EntityNotFoundException, DomainValidationException


class InvalidUserInputError(BaseAppException):
    """Backward-compatible alias for InvalidUserInputException."""
    def __init__(
        self,
        field_errors: Dict[str, List[str]],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class UserAuthenticationError(BaseAppException):
    """Backward-compatible alias for InvalidCredentialsException."""
    def __init__(
        self,
        email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            email=email,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


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
    """Exception for invalid user input data."""
    
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
            "reason": "User input validation failed"
        })
        
        if not user_message:
            user_message = "Please provide valid input data."
            
        super().__init__(
            message="Invalid user input",
            field_errors=field_errors,
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
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        lookup_params = lookup_params or {}
        if user_id:
            lookup_params["id"] = user_id
        if email:
            lookup_params["email"] = email
            
        if not user_message:
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
        user_message: Optional[str] = None
    ):
        identifier = email or username
        message = f"User already exists"
        if identifier:
            message = f"User with { 'email' if email else 'username' } '{identifier}' already exists"
            
        details = details or {}
        details.update({
            "email": email,
            "username": username,
            "reason": "User with provided credentials already exists"
        })
        
        if not user_message:
            user_message = "An account with this email already exists. Please use a different email or login."
            
        super().__init__(
            rule_name="UNIQUE_USER_IDENTITY",
            message=message,
            rule_description="User email and username must be unique",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class InvalidCredentialsException(UserException):
    """Exception for invalid login credentials."""
    
    def __init__(
        self,
        email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "email": email,
            "reason": "Invalid email or password"
        })
        
        if not user_message:
            user_message = "Invalid email or password. Please try again."
            
        super().__init__(
            message="Invalid login credentials",
            error_code="INVALID_CREDENTIALS",
            status_code=401,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
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


class InsufficientPermissionsException(BusinessRuleException):
    """Exception when user lacks required permissions."""
    
    def __init__(
        self,
        user_id: str,
        required_permission: str,
        user_permissions: List[str],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "required_permission": required_permission,
            "user_permissions": user_permissions,
            "reason": "User lacks required permissions"
        })
        
        if not user_message:
            user_message = "You don't have permission to perform this action."
            
        super().__init__(
            rule_name="PERMISSION_REQUIREMENT",
            message=f"User {user_id} lacks permission: {required_permission}",
            rule_description="Users must have appropriate permissions for actions",
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