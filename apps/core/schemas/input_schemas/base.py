from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any
from decimal import Decimal

class BaseSchema(BaseModel):
    """Base schema for all input schemas with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }
    )