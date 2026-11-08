"""
Shared application exception definitions.
"""

from .accounts import AccountException
from .attendance import AttendanceException, AttendanceNotFound, AttendanceConflict
from .base import ApplicationException
from .codes import ErrorCode
from .finance import FinanceException, FinanceAccessDenied, FinanceConflict
from .members import MemberException, MemberNotFound, MemberAccessDenied, MemberConflict
from .zones import ZoneException, ZoneNotFound, ZoneAccessDenied, ZoneConflict

__all__ = [
    "ApplicationException",
    "ErrorCode",
    "AccountException",
    "ZoneException",
    "ZoneNotFound",
    "ZoneAccessDenied",
    "ZoneConflict",
    "MemberException",
    "MemberNotFound",
    "MemberAccessDenied",
    "MemberConflict",
    "AttendanceException",
    "AttendanceNotFound",
    "AttendanceConflict",
    "FinanceException",
    "FinanceAccessDenied",
    "FinanceConflict",
]
