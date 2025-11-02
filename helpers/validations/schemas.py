from pydantic import BaseModel, Field, root_validator, validator
from typing import Optional, Dict, Any
from rules import (
    validate_email,
    validate_username,
    validate_phone,
    validate_password,
)

class BaseSchema(BaseModel):
    class Config:
        extra = "forbid"
        anystr_strip_whitespace = True
        allow_population_by_field_name = True

    def dict_safe(self, *, include=None, exclude=None, by_alias=False):
        raw = self.dict(include=include, exclude=exclude, by_alias=by_alias)
        secrets = getattr(self, "__secret_fields__", [])
        for s in secrets:
            if s in raw:
                raw[s] = "******"
        return raw


# ----------------------------
# User Schemas
# ----------------------------
class UserCreateSchema(BaseSchema):
    username: str = Field(..., min_length=3, max_length=150)
    email: str
    password: str = Field(..., min_length=8)
    phone: Optional[str] = None
    full_name: Optional[str] = None

    __secret_fields__ = ["password"]

    _validate_username = validator("username", allow_reuse=True)(validate_username)
    _validate_email = validator("email", allow_reuse=True)(validate_email)
    _validate_password = validator("password", allow_reuse=True)(validate_password)
    _validate_phone = validator("phone", allow_reuse=True)(validate_phone)


class UserUpdateSchema(BaseSchema):
    username: Optional[str] = Field(None, min_length=3, max_length=150)
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    phone: Optional[str] = None
    full_name: Optional[str] = None

    __secret_fields__ = ["password"]

    _validate_username = validator("username", allow_reuse=True)(validate_username)
    _validate_email = validator("email", allow_reuse=True)(validate_email)
    _validate_password = validator("password", allow_reuse=True)(validate_password)
    _validate_phone = validator("phone", allow_reuse=True)(validate_phone)

    @root_validator
    def ensure_non_empty(cls, values: Dict[str, Any]):
        if not any(values.values()):
            raise ValueError("At least one field must be provided for update.")
        return values
