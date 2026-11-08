"""Finance-related application exceptions."""

from rest_framework import status

from .base import ApplicationException


class FinanceException(ApplicationException):
    default_code = "FINANCE_ERROR"
    default_message = "A finance operation failed."
    default_status_code = status.HTTP_400_BAD_REQUEST


class FinanceAccessDenied(FinanceException):
    default_code = "FINANCE_ACCESS_DENIED"
    default_message = "You do not have permission to access financial data."
    default_status_code = status.HTTP_403_FORBIDDEN


class FinanceConflict(FinanceException):
    default_code = "FINANCE_CONFLICT"
    default_message = "The finance operation conflicts with existing data."
    default_status_code = status.HTTP_409_CONFLICT
