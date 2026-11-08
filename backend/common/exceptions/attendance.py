"""Attendance-related application exceptions."""

from rest_framework import status

from .base import ApplicationException


class AttendanceException(ApplicationException):
    default_code = "ATTENDANCE_ERROR"
    default_message = "An attendance operation failed."
    default_status_code = status.HTTP_400_BAD_REQUEST


class AttendanceNotFound(AttendanceException):
    default_code = "ATTENDANCE_NOT_FOUND"
    default_message = "The requested attendance record was not found."
    default_status_code = status.HTTP_404_NOT_FOUND


class AttendanceConflict(AttendanceException):
    default_code = "ATTENDANCE_CONFLICT"
    default_message = "The attendance operation conflicts with existing data."
    default_status_code = status.HTTP_409_CONFLICT
