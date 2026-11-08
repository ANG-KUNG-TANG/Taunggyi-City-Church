"""Zone-related application exceptions."""

from rest_framework import status

from .base import ApplicationException


class ZoneException(ApplicationException):
    default_code = "ZONE_ERROR"
    default_message = "A zone operation failed."
    default_status_code = status.HTTP_400_BAD_REQUEST


class ZoneNotFound(ZoneException):
    default_code = "ZONE_NOT_FOUND"
    default_message = "The requested zone was not found."
    default_status_code = status.HTTP_404_NOT_FOUND


class ZoneAccessDenied(ZoneException):
    default_code = "ZONE_ACCESS_DENIED"
    default_message = "You do not have permission to access this zone."
    default_status_code = status.HTTP_403_FORBIDDEN


class ZoneConflict(ZoneException):
    default_code = "ZONE_CONFLICT"
    default_message = "The zone operation conflicts with existing data."
    default_status_code = status.HTTP_409_CONFLICT
