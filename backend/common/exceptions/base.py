"""
Base exception for application-level errors.

Application exceptions provide a stable error code, a safe client-facing
message, optional details, and an HTTP status code.
"""

from rest_framework import status


class ApplicationException(Exception):
    """Base class for expected application-level exceptions."""

    default_code = "APPLICATION_ERROR"
    default_message = "An application error occurred."
    default_status_code = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        message=None,
        *,
        code=None,
        details=None,
        status_code=None,
    ):
        self.code = code or self.default_code
        self.message = message or self.default_message
        self.details = details
        self.status_code = status_code or self.default_status_code

        super().__init__(self.message)

    def to_dict(self):
        """Return the structured application error representation."""

        error = {
            "code": self.code,
            "message": self.message,
        }

        if self.details is not None:
            error["details"] = self.details

        return error
