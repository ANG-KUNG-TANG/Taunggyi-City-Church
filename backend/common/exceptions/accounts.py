"""Account-related application exceptions."""

from rest_framework import status

from .base import ApplicationException


class AccountException(ApplicationException):
    default_code = "ACCOUNT_ERROR"
    default_message = "An account operation failed."
    default_status_code = status.HTTP_400_BAD_REQUEST
