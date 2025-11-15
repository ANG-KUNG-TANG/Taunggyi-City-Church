
from typing import Dict, Any, Optional, List

from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, DomainOperationException, EntityNotFoundException, ValidationException
from apps.core.core_exceptions.integration import DatabaseConnectionException

class UserException(BaseAppException):
    """Base exception for user-related business errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "USER_ERROR",
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


class UserTechnicalException(BaseAppException):
    """Base exception for user-related technical errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "USER_TECHNICAL_ERROR",
        status_code: int = 500,
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
            cause=cause,
            is_critical=True
        )


# Authentication & Authorization Exceptions
class UserAuthenticationException(BusinessRuleException):
    def __init__(
        self,
        email: str = "",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if email:
            details["email"] = email
            
        super().__init__(
            rule_name="AUTHENTICATION_REQUIRED",
            message=f"Authentication failed for user: {email}" if email else "Authentication failed",
            rule_description="Valid authentication is required to access this resource",
            details=details,
            context=context,
            cause=cause
        )


class InvalidCredentialsException(UserAuthenticationException):
    def __init__(
        self,
        email: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "email": email,
            "reason": "Invalid email or password"
        })
            
        super().__init__(
            email=email,
            details=details,
            context=context,
            cause=cause
        )


class AccountLockedException(UserAuthenticationException):
    def __init__(
        self,
        email: str,
        lockout_duration: int = 30,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "email": email,
            "reason": "Account temporarily locked due to failed login attempts",
            "lockout_duration_minutes": lockout_duration
        })
            
        super().__init__(
            email=email,
            details=details,
            context=context,
            cause=cause
        )


class InactiveAccountException(UserAuthenticationException):
    def __init__(
        self,
        email: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "email": email,
            "reason": "Account is inactive"
        })
            
        super().__init__(
            email=email,
            details=details,
            context=context,
            cause=cause
        )


class PendingApprovalException(UserAuthenticationException):
    def __init__(
        self,
        email: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "email": email,
            "reason": "Account pending approval"
        })
            
        super().__init__(
            email=email,
            details=details,
            context=context,
            cause=cause
        )


class SuspendedAccountException(UserAuthenticationException):
    def __init__(
        self,
        email: str,
        reason: str = "",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "email": email,
            "reason": f"Account suspended: {reason}" if reason else "Account suspended"
        })
            
        super().__init__(
            email=email,
            details=details,
            context=context,
            cause=cause
        )
        
class InvalidUserInputException(ValidationException):
    def __init__(
        self,
        message: str = "User input validation failed",
        field_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            field_errors=field_errors or {},
            details=details,
            context=context,
            cause=cause
        )
# Permission & Role Exceptions
class UserPermissionException(BusinessRuleException):
    """Base permission exception for user operations."""
    
    def __init__(
        self,
        user_id: str,
        permission: str,
        resource: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "permission": permission,
            "resource": resource
        })
            
        super().__init__(
            rule_name="PERMISSION_REQUIRED",
            message=f"User {user_id} lacks permission {permission} for resource {resource}",
            rule_description="Users must have appropriate permissions to perform this operation",
            details=details,
            context=context,
            cause=cause
        )


class InsufficientRoleException(UserPermissionException):
    def __init__(
        self,
        user_id: str,
        current_role: str,
        required_role: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "current_role": current_role,
            "required_role": required_role,
            "operation": operation
        })
            
        super().__init__(
            user_id=user_id,
            permission=required_role,
            resource=operation,
            details=details,
            context=context,
            cause=cause
        )


class CannotModifyOwnRoleException(UserPermissionException):
    def __init__(
        self,
        user_id: str,
        target_role: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "reason": "Users cannot modify their own role",
            "target_role": target_role
        })
            
        super().__init__(
            user_id=user_id,
            permission="MODIFY_OWN_ROLE",
            resource="UserRole",
            details=details,
            context=context,
            cause=cause
        )


class CannotDeleteSelfException(UserPermissionException):
    def __init__(
        self,
        user_id: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "reason": "Users cannot delete their own account"
        })
            
        super().__init__(
            user_id=user_id,
            permission="DELETE_SELF",
            resource="UserAccount",
            details=details,
            context=context,
            cause=cause
        )


class CannotDemoteSuperAdminException(UserPermissionException):
    def __init__(
        self,
        user_id: str,
        target_user_id: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "reason": "Cannot modify Super Administrator roles",
            "target_user_id": target_user_id
        })
            
        super().__init__(
            user_id=user_id,
            permission="DEMOTE_SUPER_ADMIN",
            resource="UserRole",
            details=details,
            context=context,
            cause=cause
        )


# User Management Exceptions
class UserNotFoundException(EntityNotFoundException):
    def __init__(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        lookup_params = lookup_params or {}
        if user_id:
            lookup_params["id"] = user_id
        if email:
            lookup_params["email"] = email
            
        super().__init__(
            entity_name="User",
            entity_id=user_id,
            lookup_params=lookup_params,
            details=details,
            context=context,
            cause=cause
        )


class UserAlreadyExistsException(BusinessRuleException):
    def __init__(
        self,
        email: str,
        existing_user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "email": email,
            "reason": "User with this email already exists"
        })
        if existing_user_id:
            details["existing_user_id"] = existing_user_id
            
        super().__init__(
            rule_name="UNIQUE_USER_EMAIL",
            message=f"User with email {email} already exists",
            rule_description="Email addresses must be unique across all users",
            details=details,
            context=context,
            cause=cause
        )


class InvalidUserDataException(ValidationException):
    def __init__(
        self,
        validation_errors: Dict[str, Any],
        field_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "validation_errors": validation_errors,
            "field_errors": field_errors or {}
        })
        
        super().__init__(
            message="User data validation failed",
            field_errors=field_errors or {},
            details=details,
            context=context,
            cause=cause
        )


class InvalidEmailException(InvalidUserDataException):
    def __init__(
        self,
        email: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        field_errors = {"email": "Invalid email format"}
        validation_errors = {"email": ["Enter a valid email address"]}
        
        super().__init__(
            validation_errors=validation_errors,
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )


class WeakPasswordException(InvalidUserDataException):
    def __init__(
        self,
        password_requirements: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        requirements = password_requirements or [
            "Minimum 8 characters",
            "At least one uppercase letter",
            "At least one lowercase letter", 
            "At least one number",
            "At least one special character"
        ]
        
        field_errors = {"password": "Password is too weak"}
        validation_errors = {"password": ["Password does not meet security requirements"]}
        
        details = details or {}
        details.update({"requirements": requirements})
        
        super().__init__(
            validation_errors=validation_errors,
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )


class InvalidAgeException(InvalidUserDataException):
    def __init__(
        self,
        age: int,
        min_age: int = 0,
        max_age: int = 120,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        field_errors = {"age": f"Invalid age: {age}"}
        validation_errors = {"age": [f"Age must be between {min_age} and {max_age}"]}
        
        super().__init__(
            validation_errors=validation_errors,
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )


# User Profile Exceptions
class ProfileUpdateException(DomainOperationException):
    def __init__(
        self,
        user_id: str,
        field: str,
        value: Any,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "field": field,
            "value": value,
            "reason": reason
        })
            
        super().__init__(
            operation="update_profile",
            entity_name="User",
            reason=reason,
            details=details,
            context=context,
            cause=cause
        )


class CannotUpdateOtherUserProfileException(UserPermissionException):
    def __init__(
        self,
        user_id: str,
        target_user_id: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "target_user_id": target_user_id,
            "reason": "Can only update your own profile unless you have admin privileges"
        })
            
        super().__init__(
            user_id=user_id,
            permission="UPDATE_OTHER_PROFILES",
            resource="UserProfile",
            details=details,
            context=context,
            cause=cause
        )


# Ministry & Role Assignment Exceptions
class InvalidRoleAssignmentException(BusinessRuleException):
    def __init__(
        self,
        user_id: str,
        current_role: str,
        target_role: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "current_role": current_role,
            "target_role": target_role,
            "reason": reason
        })
            
        super().__init__(
            rule_name="VALID_ROLE_ASSIGNMENT",
            message=f"Cannot assign role {target_role} to user {user_id}",
            rule_description="Role assignments must follow business rules and hierarchy",
            details=details,
            context=context,
            cause=cause
        )


class MinistryAssignmentException(DomainOperationException):
    def __init__(
        self,
        user_id: str,
        ministry_id: str,
        operation: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "ministry_id": ministry_id,
            "operation": operation,
            "reason": reason
        })
            
        super().__init__(
            operation=operation,
            entity_name="UserMinistry",
            reason=reason,
            details=details,
            context=context,
            cause=cause
        )


class DuplicateMinistryAssignmentException(MinistryAssignmentException):
    def __init__(
        self,
        user_id: str,
        ministry_id: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            user_id=user_id,
            ministry_id=ministry_id,
            operation="assign",
            reason="User is already assigned to this ministry",
            details=details,
            context=context,
            cause=cause
        )


# Bulk User Operations Exceptions
class BulkUserOperationException(UserException):
    def __init__(
        self,
        operation: str,
        successful: int,
        failed: int,
        errors: List[Dict[str, Any]],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "operation": operation,
            "successful_count": successful,
            "failed_count": failed,
            "errors": errors
        })
            
        super().__init__(
            message=f"Bulk user {operation} completed with {successful} successes and {failed} failures",
            error_code="BULK_OPERATION_FAILED",
            status_code=400,
            details=details,
            context=context,
            cause=cause
        )


class UserImportException(BulkUserOperationException):
    def __init__(
        self,
        successful: int,
        failed: int,
        errors: List[Dict[str, Any]],
        file_type: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "file_type": file_type,
            "reason": "User import failed for some records"
        })
            
        super().__init__(
            operation="import",
            successful=successful,
            failed=failed,
            errors=errors,
            details=details,
            context=context,
            cause=cause
        )


# Technical User Exceptions
class UserDataAccessException(UserTechnicalException):
    def __init__(
        self,
        operation: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({"operation": operation})
        if user_id:
            details["user_id"] = user_id
            
        super().__init__(
            message=f"Data access error during user {operation}",
            error_code="DATA_ACCESS_ERROR",
            details=details,
            context=context,
            cause=cause
        )


class UserRepositoryException(DatabaseConnectionException):
    def __init__(
        self,
        operation: str,
        repository_method: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "operation": operation,
            "repository_method": repository_method,
            "error_type": type(cause).__name__ if cause else "Unknown"
        })
            
        super().__init__(
            message=f"Repository error during {operation}",
            database_type="user_repository",
            operation=repository_method,
            details=details,
            context=context,
            cause=cause
        )


class PasswordHashingException(UserTechnicalException):
    def __init__(
        self,
        user_id: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "reason": "Failed to securely hash password"
        })
            
        super().__init__(
            message=f"Password hashing failed for user {user_id}",
            error_code="SECURITY_ERROR",
            details=details,
            context=context,
            cause=cause
        )


class UserSessionException(UserTechnicalException):
    def __init__(
        self,
        user_id: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "operation": operation
        })
            
        super().__init__(
            message=f"Session error during {operation} for user {user_id}",
            error_code="SESSION_ERROR",
            details=details,
            context=context,
            cause=cause
        )


# Church-Specific User Exceptions
class MembershipStatusException(BusinessRuleException):
    def __init__(
        self,
        user_id: str,
        current_status: str,
        target_status: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "current_status": current_status,
            "target_status": target_status,
            "reason": reason
        })
            
        super().__init__(
            rule_name="VALID_MEMBERSHIP_TRANSITION",
            message=f"Cannot change membership status from {current_status} to {target_status}",
            rule_description="Membership status changes must follow valid transitions",
            details=details,
            context=context,
            cause=cause
        )


class BaptismRecordException(ValidationException):
    def __init__(
        self,
        user_id: str,
        baptism_date: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "baptism_date": baptism_date,
            "reason": reason
        })
        
        field_errors = {"baptism_date": [reason]}
            
        super().__init__(
            message=f"Invalid baptism record for user {user_id}",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )

   
    
class FamilyRelationshipException(ValidationException):
    def __init__(
        self,
        user_id: str,
        family_member_id: str,
        relationship: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "family_member_id": family_member_id,
            "relationship": relationship,
            "reason": reason
        })
        
        field_errors = {"family_relationships": [reason]}
            
        super().__init__(
            message=f"Invalid family relationship for user {user_id}",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )


class UnauthorizedActionException(UserPermissionException):
    def __init__(
        self,
        user_id: str,
        action: str,
        resource: str = "",
        reason: str = "Unauthorized action",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        permission = required_permission or f"PERFORM_{action.upper()}"
        details = details or {}
        details.update({
            "action": action,
            "resource": resource or action,
            "reason": reason,
            "required_permission": permission
        })
            
        super().__init__(
            user_id=user_id,
            permission=permission,
            resource=resource or action,
            details=details,
            context=context,
            cause=cause
        )


# Utility functions for user exceptions
class UserExceptionFactory:
    """Factory for creating user exceptions with consistent formatting"""
    
    @staticmethod
    def not_found(user_identifier: str, identifier_type: str = "id") -> UserNotFoundException:
        """Create UserNotFoundException with consistent formatting"""
        if identifier_type == "email":
            return UserNotFoundException(email=user_identifier)
        else:
            return UserNotFoundException(user_id=user_identifier)
    
    @staticmethod
    def permission_denied(user_id: str, operation: str, required_permission: str) -> UserPermissionException:
        """Create permission denied exception"""
        return UserPermissionException(
            user_id=user_id,
            permission=required_permission,
            resource=operation
        )
    
    @staticmethod
    def validation_error(field: str, error_message: str, value: Any = None) -> InvalidUserDataException:
        """Create validation error for a specific field"""
        errors = {field: [error_message]}
        field_errors = {field: f"Invalid value: {value}"} if value is not None else {}
        return InvalidUserDataException(
            validation_errors=errors,
            field_errors=field_errors
        )
    
    @staticmethod
    def bulk_operation(operation: str, results: List[Dict[str, Any]]) -> BulkUserOperationException:
        """Create bulk operation exception from results"""
        successful = sum(1 for r in results if r.get('success'))
        failed = len(results) - successful
        errors = [r for r in results if not r.get('success')]
        
        return BulkUserOperationException(
            operation=operation,
            successful=successful,
            failed=failed,
            errors=errors
        )