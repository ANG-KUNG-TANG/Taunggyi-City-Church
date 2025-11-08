from typing import Dict, List
from helpers.exceptions.domain.base_exception import BusinessException
from helpers.exceptions.domain.domain_exceptions import ObjectNotFoundException
from .error_codes import ErrorCode, Domain

class SermonException(BusinessException):
    def __init__(self, message: str, error_code: ErrorCode, details: Dict = None, user_message: str = None):
        super().__init__(
            message=message,
            error_code=error_code,
            domain=Domain.SERMON,
            status_code=400,
            details=details,
            user_message=user_message
        )

class SermonNotFoundException(ObjectNotFoundException):
    def __init__(self, sermon_id: str = "", cause: Exception = None):
        super().__init__(
            model="Sermon",
            lookup_params={"id": sermon_id} if sermon_id else {},
            domain=Domain.SERMON,
            cause=cause
        )

class SermonMediaNotFoundException(SermonException):
    def __init__(self, media_id: str, sermon_id: str = ""):
        details = {"media_id": media_id}
        if sermon_id: details["sermon_id"] = sermon_id
            
        super().__init__(
            message=f"Sermon media {media_id} not found",
            error_code=ErrorCode.SERMON_MEDIA_NOT_FOUND,
            details=details,
            user_message="The requested media file was not found."
        )

class MediaUploadFailedException(SermonException):
    def __init__(self, sermon_id: str, file_name: str, reason: str):
        super().__init__(
            message=f"Media upload failed for sermon {sermon_id}",
            error_code=ErrorCode.MEDIA_UPLOAD_FAILED,
            details={
                "sermon_id": sermon_id,
                "file_name": file_name,
                "reason": reason
            },
            user_message="Failed to upload media file. Please try again."
        )

class InvalidMediaTypeException(SermonException):
    def __init__(self, file_name: str, allowed_types: List[str], actual_type: str):
        super().__init__(
            message=f"Invalid media type for file {file_name}",
            error_code=ErrorCode.INVALID_MEDIA_TYPE,
            details={
                "file_name": file_name,
                "allowed_types": allowed_types,
                "actual_type": actual_type,
                "reason": "File type not supported"
            },
            user_message=f"File type not supported. Allowed types: {', '.join(allowed_types)}"
        )

class BibleReferenceInvalidException(SermonException):
    def __init__(self, bible_reference: str, reason: str):
        super().__init__(
            message=f"Invalid Bible reference: {bible_reference}",
            error_code=ErrorCode.BIBLE_REFERENCE_INVALID,
            details={
                "bible_reference": bible_reference,
                "reason": reason
            },
            user_message="Invalid Bible reference. Please check the format."
        )

class SermonPublishException(SermonException):
    def __init__(self, sermon_id: str, sermon_title: str, reason: str):
        super().__init__(
            message=f"Cannot publish sermon {sermon_title}",
            error_code=ErrorCode.SERMON_PUBLISH_ERROR,
            details={
                "sermon_id": sermon_id,
                "sermon_title": sermon_title,
                "reason": reason
            },
            user_message="Unable to publish sermon. Please check sermon details."
        )

class SermonArchiveException(SermonException):
    def __init__(self, sermon_id: str, sermon_title: str, reason: str):
        super().__init__(
            message=f"Cannot archive sermon {sermon_title}",
            error_code=ErrorCode.SERMON_ARCHIVE_ERROR,
            details={
                "sermon_id": sermon_id,
                "sermon_title": sermon_title,
                "reason": reason
            },
            user_message="Unable to archive sermon."
        )

class MediaProcessingException(SermonException):
    def __init__(self, sermon_id: str, file_name: str, processing_step: str, reason: str):
        super().__init__(
            message=f"Media processing failed for {file_name}",
            error_code=ErrorCode.MEDIA_PROCESSING_ERROR,
            details={
                "sermon_id": sermon_id,
                "file_name": file_name,
                "processing_step": processing_step,
                "reason": reason
            },
            user_message="Media processing failed. Please try again with a different file."
        )

class MediaDurationInvalidException(SermonException):
    def __init__(self, file_name: str, duration: int, max_duration: int):
        super().__init__(
            message=f"Media duration {duration}s exceeds maximum {max_duration}s",
            error_code=ErrorCode.MEDIA_DURATION_INVALID,
            details={
                "file_name": file_name,
                "duration": duration,
                "max_duration": max_duration,
                "reason": "Media file too long"
            },
            user_message=f"Media file is too long. Maximum duration is {max_duration} seconds."
        )

class SermonAlreadyPublishedException(SermonException):
    def __init__(self, sermon_id: str, sermon_title: str):
        super().__init__(
            message=f"Sermon {sermon_title} is already published",
            error_code=ErrorCode.SERMON_ALREADY_PUBLISHED,
            details={
                "sermon_id": sermon_id,
                "sermon_title": sermon_title,
                "reason": "Cannot modify published sermon"
            },
            user_message="This sermon is already published and cannot be modified."
        )

class MediaStorageException(SermonException):
    def __init__(self, sermon_id: str, file_name: str, operation: str, reason: str):
        super().__init__(
            message=f"Media storage error for {file_name}",
            error_code=ErrorCode.MEDIA_STORAGE_ERROR,
            details={
                "sermon_id": sermon_id,
                "file_name": file_name,
                "operation": operation,
                "reason": reason
            },
            user_message="Media storage error. Please try again."
        )