from typing import Generic, TypeVar, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper used in the View layer.

    - No HTTP logic
    - No Django or DRF imports
    - Pure data structure
    """

    success: bool = Field(..., description="Indicates if the operation was successful")
    message: str = Field(..., description="Human-readable status message")
    data: Optional[T] = Field(None, description="Payload or domain output")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status_code: int = Field(default=200, description="HTTP status code")

    # New optional debugging / machine-readable fields for errors
    error_type: Optional[str] = Field(
        None, description="Optional machine-readable error type or code (for clients)"
    )
    errors: Optional[Any] = Field(
        None, description="Optional structured error details (e.g. validation errors)"
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        },
        arbitrary_types_allowed=True
    )

    # ----------------------------------------
    # SUCCESS RESPONSE
    # ----------------------------------------
    @classmethod
    def create_success(
        cls,
        message: str = "Success",
        data: Optional[T] = None,
        status_code: int = 200
    ) -> "APIResponse[T]":
        return cls(
            success=True,
            message=message,
            data=data,
            timestamp=datetime.utcnow(),
            status_code=status_code,
            error_type=None,
            errors=None
        )

    # ----------------------------------------
    # ERROR RESPONSE
    # ----------------------------------------
    @classmethod
    def create_error(
        cls,
        message: str = "Error",
        data: Optional[Any] = None,
        status_code: int = 400,
        error_type: Optional[str] = None,
        errors: Optional[Any] = None,
    ) -> "APIResponse[Any]":
        """
        Create a standardized error response.

        - `error_type` is a short machine-readable string (e.g. "VALIDATION_ERROR").
        - `errors` can hold structured validation error details.
        - `data` remains available if you want to include additional payload.
        """
        return cls(
            success=False,
            message=message,
            data=data,
            timestamp=datetime.utcnow(),
            status_code=status_code,
            error_type=error_type,
            errors=errors
        )

    # ----------------------------------------
    # DICT SERIALIZATION
    # ----------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert response object into a JSON-safe dictionary.
        """
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.status_code,
            "error_type": self.error_type,
            "errors": self.errors,
        }
