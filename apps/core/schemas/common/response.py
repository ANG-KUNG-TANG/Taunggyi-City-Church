from typing import Generic, TypeVar, Optional, Any, Dict, List
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
            status_code=status_code
        )

    # ----------------------------------------
    # ERROR RESPONSE
    # ----------------------------------------
    @classmethod
    def create_error(
        cls,
        message: str = "Error",
        data: Optional[Any] = None,
        status_code: int = 400
    ) -> "APIResponse[Any]":
        return cls(
            success=False,
            message=message,
            data=data,
            timestamp=datetime.utcnow(),
            status_code=status_code
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
        }


class ErrorResponse(BaseModel):
    """
    Structured error response for internal use if needed.
    Not used directly in views under Design A.
    """

    code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ValidationErrorResponse(ErrorResponse):
    """
    Specialized error response for validation failures.
    """

    @classmethod
    def from_errors(cls, errors: Dict[str, Any]):
        return cls(
            code="VALIDATION_ERROR",
            message="Validation failed",
            details=errors
        )


class ListResponse(BaseModel, Generic[T]):
    """
    Generic list response wrapper for paginated or bulk data.
    """

    items: List[T]
    total: int

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class SuccessResponse(BaseModel):
    """
    Simple success response for non-domain operations.
    """

    success: bool = True
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
