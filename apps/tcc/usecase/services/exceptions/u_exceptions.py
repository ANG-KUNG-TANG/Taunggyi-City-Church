# user_exceptions.py
from typing import Dict, Any, Optional, List
from helpers.exceptions.domain.base_exception import BusinessException, TechnicalException
from helpers.exceptions.domain.domain_exceptions import (
    ObjectNotFoundException, 
    ObjectValidationException, 
    AuthenticationException,
    PermissionException
)
from error_codes import ErrorCode

class UserException(BusinessException):
    """Base exception for all user-related business errors"""
    pass

class UserTechnicalException(TechnicalException):
    """Base exception for all user-related technical errors"""
    pass

# Authentication & Authorization Exceptions
class UserAuthenticationException(AuthenticationException):
    def __init__(self, email: str = "", details: Dict = None):
        super().__init__(
            message=f"Authentication failed for user: {email}" if email else "Authentication failed",
            details=details or {}
        )

class InvalidCredentialsException(UserAuthenticationException):
    def __init__(self, email: str):
        super().__init__(
            email=email,
            details={
                "email": email,
                "reason": "Invalid email or password"
            }
        )

class AccountLockedException(UserAuthenticationException):
    def __init__(self, email: str, lockout_duration: int = 30):
        super().__init__(
            email=email,
            details={
                "email": email,
                "reason": "Account temporarily locked due to failed login attempts",
                "lockout_duration_minutes": lockout_duration
            }
        )

class InactiveAccountException(UserAuthenticationException):
    def __init__(self, email: str):
        super().__init__(
            email=email,
            details={
                "email": email,
                "reason": "Account is inactive"
            }
        )

class PendingApprovalException(UserAuthenticationException):
    def __init__(self, email: str):
        super().__init__(
            email=email,
            details={
                "email": email,
                "reason": "Account pending approval"
            }
        )

class SuspendedAccountException(UserAuthenticationException):
    def __init__(self, email: str, reason: str = ""):
        super().__init__(
            email=email,
            details={
                "email": email,
                "reason": f"Account suspended: {reason}" if reason else "Account suspended"
            }
        )

# Permission & Role Exceptions
class UserPermissionException(PermissionException):
    """Base permission exception for user operations"""
    pass

class InsufficientRoleException(UserPermissionException):
    def __init__(self, user_id: str, current_role: str, required_role: str, operation: str):
        super().__init__(
            user=user_id,
            permission=required_role,
            resource=operation
        )
        self.details.update({
            "current_role": current_role,
            "required_role": required_role,
            "operation": operation
        })

class CannotModifyOwnRoleException(UserPermissionException):
    def __init__(self, user_id: str, target_role: str):
        super().__init__(
            user=user_id,
            permission="MODIFY_OWN_ROLE",
            resource="UserRole"
        )
        self.details.update({
            "reason": "Users cannot modify their own role",
            "target_role": target_role
        })

class CannotDeleteSelfException(UserPermissionException):
    def __init__(self, user_id: str):
        super().__init__(
            user=user_id,
            permission="DELETE_SELF",
            resource="UserAccount"
        )
        self.details.update({
            "reason": "Users cannot delete their own account"
        })

class CannotDemoteSuperAdminException(UserPermissionException):
    def __init__(self, user_id: str, target_user_id: str):
        super().__init__(
            user=user_id,
            permission="DEMOTE_SUPER_ADMIN",
            resource="UserRole"
        )
        self.details.update({
            "reason": "Cannot modify Super Administrator roles",
            "target_user_id": target_user_id
        })

# User Management Exceptions
class UserNotFoundException(ObjectNotFoundException):
    def __init__(self, user_id: str = "", email: str = "", cause: Exception = None):
        lookup_params = {}
        if user_id:
            lookup_params["id"] = user_id
        if email:
            lookup_params["email"] = email
            
        super().__init__(
            model="User",
            lookup_params=lookup_params,
            cause=cause
        )

class UserAlreadyExistsException(UserException):
    def __init__(self, email: str, existing_user_id: str = None):
        details = {
            "email": email,
            "reason": "User with this email already exists"
        }
        if existing_user_id:
            details["existing_user_id"] = existing_user_id
            
        super().__init__(
            message=f"User with email {email} already exists",
            error_code=ErrorCode.ALREADY_EXISTS.value,
            status_code=409,
            details=details
        )

class InvalidUserDataException(ObjectValidationException):
    def __init__(self, validation_errors: Dict, field_errors: Dict = None):
        details = {
            "validation_errors": validation_errors,
            "field_errors": field_errors or {}
        }
        
        super().__init__(
            model="User",
            validation_errors=details,
            cause=None
        )

class InvalidEmailException(InvalidUserDataException):
    def __init__(self, email: str):
        super().__init__(
            validation_errors={"email": ["Enter a valid email address"]},
            field_errors={"email": f"Invalid email format: {email}"}
        )

class WeakPasswordException(InvalidUserDataException):
    def __init__(self, password_requirements: List[str] = None):
        details = {
            "password": ["Password does not meet security requirements"],
            "requirements": password_requirements or [
                "Minimum 8 characters",
                "At least one uppercase letter",
                "At least one lowercase letter", 
                "At least one number",
                "At least one special character"
            ]
        }
        super().__init__(
            validation_errors=details,
            field_errors={"password": "Password is too weak"}
        )

class InvalidAgeException(InvalidUserDataException):
    def __init__(self, age: int, min_age: int = 0, max_age: int = 120):
        super().__init__(
            validation_errors={"age": [f"Age must be between {min_age} and {max_age}"]},
            field_errors={"age": f"Invalid age: {age}"}
        )

# User Profile Exceptions
class ProfileUpdateException(UserException):
    def __init__(self, user_id: str, field: str, value: Any, reason: str):
        super().__init__(
            message=f"Failed to update profile for user {user_id}",
            error_code=ErrorCode.VALIDATION_ERROR.value,
            status_code=400,
            details={
                "user_id": user_id,
                "field": field,
                "value": value,
                "reason": reason
            }
        )

class CannotUpdateOtherUserProfileException(UserPermissionException):
    def __init__(self, user_id: str, target_user_id: str):
        super().__init__(
            user=user_id,
            permission="UPDATE_OTHER_PROFILES",
            resource="UserProfile"
        )
        self.details.update({
            "target_user_id": target_user_id,
            "reason": "Can only update your own profile unless you have admin privileges"
        })

# Ministry & Role Assignment Exceptions
class InvalidRoleAssignmentException(UserException):
    def __init__(self, user_id: str, current_role: str, target_role: str, reason: str):
        super().__init__(
            message=f"Cannot assign role {target_role} to user {user_id}",
            error_code=ErrorCode.INVALID_OPERATION.value,
            status_code=400,
            details={
                "user_id": user_id,
                "current_role": current_role,
                "target_role": target_role,
                "reason": reason
            }
        )

class MinistryAssignmentException(UserException):
    def __init__(self, user_id: str, ministry_id: str, operation: str, reason: str):
        super().__init__(
            message=f"Failed to {operation} user {user_id} to ministry {ministry_id}",
            error_code=ErrorCode.INVALID_OPERATION.value,
            status_code=400,
            details={
                "user_id": user_id,
                "ministry_id": ministry_id,
                "operation": operation,
                "reason": reason
            }
        )

class DuplicateMinistryAssignmentException(MinistryAssignmentException):
    def __init__(self, user_id: str, ministry_id: str):
        super().__init__(
            user_id=user_id,
            ministry_id=ministry_id,
            operation="assign",
            reason="User is already assigned to this ministry"
        )

# Bulk User Operations Exceptions
class BulkUserOperationException(UserException):
    def __init__(self, operation: str, successful: int, failed: int, errors: List[Dict]):
        super().__init__(
            message=f"Bulk user {operation} completed with {successful} successes and {failed} failures",
            error_code=ErrorCode.BULK_OPERATION_FAILED.value,
            status_code=400,
            details={
                "operation": operation,
                "successful_count": successful,
                "failed_count": failed,
                "errors": errors
            }
        )

class UserImportException(BulkUserOperationException):
    def __init__(self, successful: int, failed: int, errors: List[Dict], file_type: str):
        super().__init__(
            operation="import",
            successful=successful,
            failed=failed,
            errors=errors
        )
        self.details.update({
            "file_type": file_type,
            "reason": "User import failed for some records"
        })

# Technical User Exceptions
class UserDataAccessException(UserTechnicalException):
    def __init__(self, operation: str, user_id: str = "", cause: Exception = None):
        details = {"operation": operation}
        if user_id:
            details["user_id"] = user_id
            
        super().__init__(
            message=f"Data access error during user {operation}",
            error_code=ErrorCode.DATA_ACCESS_ERROR.value,
            status_code=500,
            details=details,
            cause=cause
        )

class UserRepositoryException(UserTechnicalException):
    def __init__(self, operation: str, repository_method: str, cause: Exception = None):
        super().__init__(
            message=f"Repository error during {operation}",
            error_code=ErrorCode.REPOSITORY_ERROR.value,
            status_code=500,
            details={
                "operation": operation,
                "repository_method": repository_method,
                "error_type": type(cause).__name__ if cause else "Unknown"
            },
            cause=cause
        )

class PasswordHashingException(UserTechnicalException):
    def __init__(self, user_id: str, cause: Exception = None):
        super().__init__(
            message=f"Password hashing failed for user {user_id}",
            error_code=ErrorCode.SECURITY_ERROR.value,
            status_code=500,
            details={
                "user_id": user_id,
                "reason": "Failed to securely hash password"
            },
            cause=cause
        )

class UserSessionException(UserTechnicalException):
    def __init__(self, user_id: str, operation: str, cause: Exception = None):
        super().__init__(
            message=f"Session error during {operation} for user {user_id}",
            error_code=ErrorCode.SESSION_ERROR.value,
            status_code=500,
            details={
                "user_id": user_id,
                "operation": operation
            },
            cause=cause
        )

# Church-Specific User Exceptions
class MembershipStatusException(UserException):
    def __init__(self, user_id: str, current_status: str, target_status: str, reason: str):
        super().__init__(
            message=f"Cannot change membership status from {current_status} to {target_status}",
            error_code=ErrorCode.INVALID_OPERATION.value,
            status_code=400,
            details={
                "user_id": user_id,
                "current_status": current_status,
                "target_status": target_status,
                "reason": reason
            }
        )

class BaptismRecordException(UserException):
    def __init__(self, user_id: str, baptism_date: str, reason: str):
        super().__init__(
            message=f"Invalid baptism record for user {user_id}",
            error_code=ErrorCode.VALIDATION_ERROR.value,
            status_code=400,
            details={
                "user_id": user_id,
                "baptism_date": baptism_date,
                "reason": reason
            }
        )

class FamilyRelationshipException(UserException):
    def __init__(self, user_id: str, family_member_id: str, relationship: str, reason: str):
        super().__init__(
            message=f"Invalid family relationship for user {user_id}",
            error_code=ErrorCode.VALIDATION_ERROR.value,
            status_code=400,
            details={
                "user_id": user_id,
                "family_member_id": family_member_id,
                "relationship": relationship,
                "reason": reason
            }
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
            user=user_id,
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
    def bulk_operation(operation: str, results: List[Dict]) -> BulkUserOperationException:
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