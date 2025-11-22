from typing import Dict, List, Optional, Any
from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, EntityNotFoundException, DomainValidationException, DomainOperationException
from apps.core.core_exceptions.integration import StorageException


class SermonException(BaseAppException):
    """Base exception for sermon-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "SERMON_ERROR",
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

class InvalidInputException(DomainValidationException):
    """Generic validation exception for invalid input payloads."""

    def __init__(
        self,
        message: str = "Invalid input",
        field_errors: Optional[Dict[str, List[str]]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        details = details or {}
        # Add field_errors to details if provided
        if field_errors:
            details["field_errors"] = field_errors
            
        super().__init__(
            message=message,
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause,
            user_message=message  # Default user message to the main message
        )
class SermonNotFoundException(EntityNotFoundException):
    """Exception when sermon is not found."""
    
    def __init__(
        self,
        sermon_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        if not user_message:
            user_message = "Sermon not found."
            
        super().__init__(
            entity_name="Sermon",
            entity_id=sermon_id,
            lookup_params=lookup_params or ({"id": sermon_id} if sermon_id else {}),
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class SermonMediaNotFoundException(EntityNotFoundException):
    """Exception when sermon media is not found."""
    
    def __init__(
        self,
        media_id: str,
        sermon_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({"media_id": media_id})
        if sermon_id:
            details["sermon_id"] = sermon_id
            
        if not user_message:
            user_message = "Sermon media not found."
            
        super().__init__(
            entity_name="SermonMedia",
            entity_id=media_id,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class MediaUploadFailedException(StorageException):
    """Exception when media upload fails."""
    
    def __init__(
        self,
        sermon_id: str,
        file_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "sermon_id": sermon_id,
            "file_name": file_name,
            "reason": reason
        })
        
        if not user_message:
            user_message = "Failed to upload media file. Please try again."
            
        super().__init__(
            message=f"Media upload failed for sermon {sermon_id}",
            storage_service="file_storage",
            operation="upload",
            file_path=file_name,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class InvalidMediaTypeException(DomainValidationException):
    """Exception when media type is not supported."""
    
    def __init__(
        self,
        file_name: str,
        allowed_types: List[str],
        actual_type: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "file_name": file_name,
            "allowed_types": allowed_types,
            "actual_type": actual_type,
            "reason": "File type not supported"
        })
        
        field_errors = {
            "media_file": [f"File type not supported. Allowed types: {', '.join(allowed_types)}"]
        }
        
        if not user_message:
            user_message = f"File type '{actual_type}' is not supported. Please use: {', '.join(allowed_types)}"
            
        super().__init__(
            message=f"Invalid media type for file {file_name}",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class BibleReferenceInvalidException(DomainValidationException):
    """Exception when Bible reference is invalid."""
    
    def __init__(
        self,
        bible_reference: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "bible_reference": bible_reference,
            "reason": reason
        })
        
        field_errors = {
            "bible_reference": ["Invalid Bible reference format"]
        }
        
        if not user_message:
            user_message = f"Invalid Bible reference: {bible_reference}"
            
        super().__init__(
            message=f"Invalid Bible reference: {bible_reference}",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class SermonPublishException(DomainOperationException):
    """Exception when sermon publishing fails."""
    
    def __init__(
        self,
        sermon_id: str,
        sermon_title: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "sermon_id": sermon_id,
            "sermon_title": sermon_title,
            "reason": reason
        })
        
        if not user_message:
            user_message = f"Failed to publish sermon '{sermon_title}'."
            
        super().__init__(
            operation="publish",
            entity_name="Sermon",
            reason=reason,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class SermonAlreadyPublishedException(BusinessRuleException):
    """Exception when trying to modify a published sermon."""
    
    def __init__(
        self,
        sermon_id: str,
        sermon_title: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "sermon_id": sermon_id,
            "sermon_title": sermon_title,
            "reason": "Cannot modify published sermon"
        })
        
        if not user_message:
            user_message = "Published sermons cannot be modified. Please create a new version."
            
        super().__init__(
            rule_name="SERMON_MODIFICATION",
            message=f"Sermon {sermon_title} is already published",
            rule_description="Published sermons are immutable",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )
        
