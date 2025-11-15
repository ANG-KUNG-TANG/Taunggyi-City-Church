from pydantic import BaseModel
from typing import List
from .constant import TokenType

class TokenPayload(BaseModel):
    # Standard claims
    iss: str
    sub: str
    aud: str
    exp: int
    iat: int
    jti: str
    typ: TokenType
    
    # Custom claims
    user_id: int
    email: str

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int