from typing import Dict, List, Optional, Any
from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import DomainOperationException, EntityNotFoundException, ValidationException
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


class SermonNotFoundException(EntityNotFoundException):
    def __init__(
        self,
        sermon_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            entity_name="Sermon",
            entity_id=sermon_id,
            lookup_params=lookup_params or ({"id": sermon_id} if sermon_id else {}),
            details=details,
            context=context,
            cause=cause
        )


class SermonMediaNotFoundException(EntityNotFoundException):
    def __init__(
        self,
        media_id: str,
        sermon_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({"media_id": media_id})
        if sermon_id:
            details["sermon_id"] = sermon_id
            
        super().__init__(
            entity_name="SermonMedia",
            entity_id=media_id,
            details=details,
            context=context,
            cause=cause
        )


class MediaUploadFailedException(StorageException):
    def __init__(
        self,
        sermon_id: str,
        file_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "sermon_id": sermon_id,
            "file_name": file_name,
            "reason": reason
        })
            
        super().__init__(
            message=f"Media upload failed for sermon {sermon_id}",
            storage_service="file_storage",
            operation="upload",
            file_path=file_name,
            details=details,
            context=context,
            cause=cause
        )


class InvalidMediaTypeException(ValidationException):
    def __init__(
        self,
        file_name: str,
        allowed_types: List[str],
        actual_type: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
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
            
        super().__init__(
            message=f"Invalid media type for file {file_name}",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )


class BibleReferenceInvalidException(ValidationException):
    def __init__(
        self,
        bible_reference: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "bible_reference": bible_reference,
            "reason": reason
        })
        
        field_errors = {
            "bible_reference": ["Invalid Bible reference format"]
        }
            
        super().__init__(
            message=f"Invalid Bible reference: {bible_reference}",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )


class SermonPublishException(DomainOperationException):
    def __init__(
        self,
        sermon_id: str,
        sermon_title: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "sermon_id": sermon_id,
            "sermon_title": sermon_title,
            "reason": reason
        })
            
        super().__init__(
            operation="publish",
            entity_name="Sermon",
            reason=reason,
            details=details,
            context=context,
            cause=cause
        )


class SermonArchiveException(DomainOperationException):
    def __init__(
        self,
        sermon_id: str,
        sermon_title: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "sermon_id": sermon_id,
            "sermon_title": sermon_title,
            "reason": reason
        })
            
        super().__init__(
            operation="archive",
            entity_name="Sermon",
            reason=reason,
            details=details,
            context=context,
            cause=cause
        )


class MediaProcessingException(SermonException):
    def __init__(
        self,
        sermon_id: str,
        file_name: str,
        processing_step: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "sermon_id": sermon_id,
            "file_name": file_name,
            "processing_step": processing_step,
            "reason": reason
        })
            
        super().__init__(
            message=f"Media processing failed for {file_name}",
            error_code="MEDIA_PROCESSING_ERROR",
            status_code=500,
            details=details,
            context=context,
            cause=cause
        )


class MediaDurationInvalidException(ValidationException):
    def __init__(
        self,
        file_name: str,
        duration: int,
        max_duration: int,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "file_name": file_name,
            "duration": duration,
            "max_duration": max_duration,
            "reason": "Media file too long"
        })
        
        field_errors = {
            "media_file": [f"Media file is too long. Maximum duration is {max_duration} seconds."]
        }
            
        super().__init__(
            message=f"Media duration {duration}s exceeds maximum {max_duration}s",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )


class SermonAlreadyPublishedException(DomainOperationException):
    def __init__(
        self,
        sermon_id: str,
        sermon_title: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "sermon_id": sermon_id,
            "sermon_title": sermon_title,
            "reason": "Cannot modify published sermon"
        })
            
        super().__init__(
            operation="modify",
            entity_name="Sermon",
            reason="Sermon is already published",
            details=details,
            context=context,
            cause=cause
        )


class MediaStorageException(StorageException):
    def __init__(
        self,
        sermon_id: str,
        file_name: str,
        operation: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "sermon_id": sermon_id,
            "file_name": file_name,
            "operation": operation,
            "reason": reason
        })
            
        super().__init__(
            message=f"Media storage error for {file_name}",
            storage_service="file_storage",
            operation=operation,
            file_path=file_name,
            details=details,
            context=context,
            cause=cause
        )