"""Member-related application exceptions."""

from rest_framework import status

from .base import ApplicationException


class MemberException(ApplicationException):
    default_code = "MEMBER_ERROR"
    default_message = "A member operation failed."
    default_status_code = status.HTTP_400_BAD_REQUEST


class MemberNotFound(MemberException):
    default_code = "MEMBER_NOT_FOUND"
    default_message = "The requested member was not found."
    default_status_code = status.HTTP_404_NOT_FOUND


class MemberAccessDenied(MemberException):
    default_code = "MEMBER_ACCESS_DENIED"
    default_message = "You do not have permission to access this member."
    default_status_code = status.HTTP_403_FORBIDDEN


class MemberConflict(MemberException):
    default_code = "MEMBER_CONFLICT"
    default_message = "The member operation conflicts with existing data."
    default_status_code = status.HTTP_409_CONFLICT
